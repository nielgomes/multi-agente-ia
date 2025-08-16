#indexer/src/main.py
import os
import json
import uuid
import magic
import logging # Importa a biblioteca de logging
from flask import Flask, request, jsonify
from qdrant_client import QdrantClient, models
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredWordDocumentLoader, UnstructuredXMLLoader, CSVLoader
import google.generativeai as genai
from chunker_customizado import chunkificar_texto_completo

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
REGISTRY_DIR = '/app/registry'

# Configura um logger mais detalhado
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

try:
    client = QdrantClient(host='qdrant', port=6333)
    app.logger.info("✅ Indexer: Conectado ao Qdrant com sucesso.")
except Exception as e:
    client = None
    app.logger.error(f"❌ Indexer: Falha ao conectar ao Qdrant: {e}")

try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY não encontrada.")
    
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
    genai.configure(api_key=api_key)
    app.logger.info("✅ Indexer: Modelo de embedding e API do Gemini carregados.")
except Exception as e:
    embeddings = None
    app.logger.error(f"❌ Indexer: Falha ao carregar o modelo de embedding: {e}")

# --- FUNÇÕES DE LÓGICA ---

def extract_text_with_gemini_multimodal(file_path: str) -> str | None:
    app.logger.info(f"  -> Tentando fallback multimodal com Gemini para: {os.path.basename(file_path)}")
    try:
        gemini_file = genai.upload_file(path=file_path)
        app.logger.info(f"  -> Ficheiro enviado para a API do Google. ID: {gemini_file.name}")
        model = genai.GenerativeModel(model_name="gemini-2.5-pro")
        response = model.generate_content(
            ["Extraia todo o conteúdo textual deste ficheiro...", gemini_file]
        )
        genai.delete_file(gemini_file.name)
        if "NENHUM_CONTEUDO_EXTRAIDO" in response.text:
            app.logger.warning("  -> Gemini não conseguiu extrair conteúdo textual útil.")
            return None
        app.logger.info("  -> ✅ Gemini extraiu conteúdo com sucesso!")
        return response.text
    except Exception as e:
        app.logger.error(f"  -> ❌ Falha no fallback multimodal: {e}")
        return None

def load_and_process_document(file_path: str) -> list[str] | None:
    app.logger.info(f"  -> Processando ficheiro: {os.path.basename(file_path)}")
    full_text, document, loader = None, None, None

    if file_path.endswith(".pdf"): loader = PyPDFLoader(file_path)
    elif file_path.endswith(".txt"): loader = TextLoader(file_path, encoding='utf-8')
    elif file_path.endswith(".docx"): loader = UnstructuredWordDocumentLoader(file_path)
    elif file_path.endswith(".csv"): loader = CSVLoader(file_path, encoding='utf-8')
    elif file_path.endswith(".xml"): loader = UnstructuredXMLLoader(file_path)

    if loader:
        try:
            document = loader.load()
            full_text = "\n\n".join([page.page_content for page in document])
        except Exception as e:
            app.logger.warning(f"  -> Erro ao carregar com o loader padrão: {e}. Tentando fallback.")
            full_text = None

    if not full_text:
        mime_type = magic.Magic(mime=True).from_file(file_path)
        if mime_type.startswith('image/') or mime_type.startswith('audio/') or 'pdf' in mime_type:
             full_text = extract_text_with_gemini_multimodal(file_path)
        else:
             app.logger.warning(f"   -> Formato de ficheiro não suportado: {os.path.basename(file_path)}")
             return None

    if not full_text: return None

    if file_path.endswith((".csv", ".xml")):
        app.logger.info("  -> Usando chunking por linha/documento para dados estruturados.")
        return [page.page_content for page in document] if document else None
    else:
        app.logger.info(f"  -> Aplicando chunker de texto customizado...")
        chunks = chunkificar_texto_completo(full_text)
        app.logger.info(f"  -> Documento dividido em {len(chunks)} chunks.")
        return chunks


# --- ENDPOINT DE INDEXAÇÃO APRIMORADO ---
@app.route("/indexar", methods=["POST"])
def indexar_agente():
    if not client or not embeddings:
        return jsonify({"erro": "Serviço de indexação não está pronto."}), 503

    data = request.get_json()
    agent_name = data.get("agente")
    agent_list = data.get("agentes")
    
    agents_to_process = []
    if agent_name:
        if agent_name == "*": # Caso especial para todos os agentes
            agents_to_process = [d for d in os.listdir(REGISTRY_DIR) if os.path.isdir(os.path.join(REGISTRY_DIR, d))]
        else:
            agents_to_process.append(agent_name)
    elif agent_list and isinstance(agent_list, list):
        agents_to_process = agent_list
    else:
        return jsonify({"erro": "É obrigatório fornecer a chave 'agente' (com uma string ou '*') ou 'agentes' (com uma lista)."}), 400

    results = []
    skipped_files = []

    for agent in agents_to_process:
        app.logger.info(f"--- Iniciando indexação para o agente: {agent} ---")
        collection_name = f"colecao_{agent}"
        knowledge_base_path = os.path.join(REGISTRY_DIR, agent, "knowledge_base")

        if not os.path.isdir(knowledge_base_path):
            results.append({"agente": agent, "status": "erro", "mensagem": "Pasta 'knowledge_base' não encontrada."})
            continue

        try:
            client.recreate_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
            )

            total_chunks, files_count = 0, 0
            
            for filename in os.listdir(knowledge_base_path):
                file_path = os.path.join(knowledge_base_path, filename)
                if os.path.isfile(file_path) and not filename.startswith('.'):
                    chunks = load_and_process_document(file_path)
                    
                    if chunks:
                        client.upsert(
                            collection_name=collection_name,
                            points=models.Batch(
                                ids=[str(uuid.uuid4()) for _ in chunks],
                                payloads=[{"text": chunk, "source": filename} for chunk in chunks],
                                vectors=[embeddings.embed_query(chunk) for chunk in chunks]
                            ),
                            wait=True
                        )
                        total_chunks += len(chunks)
                        files_count += 1
                    else:
                        skipped_files.append({"agente": agent, "arquivo": filename})
            
            results.append({
                "agente": agent, "status": "sucesso", 
                "mensagem": f"Indexação concluída. {files_count} arquivos processados, {total_chunks} chunks adicionados."
            })
        except Exception as e:
            results.append({"agente": agent, "status": "erro", "mensagem": str(e)})
            app.logger.error(f"Erro durante a indexação do agente {agent}: {e}", exc_info=True)

    return jsonify({
        "resumo_da_operacao": results,
        "arquivos_ignorados": skipped_files
    })

@app.route("/apagar", methods=["DELETE"])
def apagar_colecao():
    if not client:
        return jsonify({"erro": "Serviço de indexação não está pronto."}), 503

    data = request.get_json()
    agent_name = data.get("agente")
    agent_list = data.get("agentes")

    agents_to_process = []
    if agent_name:
        if agent_name == "*":
            agents_to_process = [d for d in os.listdir(REGISTRY_DIR) if os.path.isdir(os.path.join(REGISTRY_DIR, d))]
        else:
            agents_to_process.append(agent_name)
    elif agent_list and isinstance(agent_list, list):
        agents_to_process = agent_list
    else:
        return jsonify({"erro": "É obrigatório fornecer a chave 'agente' (com uma string ou '*') ou 'agentes' (com uma lista)."}), 400

    results = []
    for agent in agents_to_process:
        collection_name = f"colecao_{agent}"
        try:
            success = client.delete_collection(collection_name=collection_name)
            if success:
                results.append({"agente": agent, "status": "sucesso", "mensagem": f"Coleção '{collection_name}' apagada."})
            else:
                results.append({"agente": agent, "status": "aviso", "mensagem": f"Operação de exclusão falhou ou coleção '{collection_name}' já não existia."})
        except Exception as e:
            # Captura o caso de a coleção não existir, que não é um erro crítico
            results.append({"agente": agent, "status": "aviso", "mensagem": f"Não foi possível apagar a coleção '{collection_name}'. Detalhes: {e}"})

    return jsonify({"resumo_da_operacao": results})