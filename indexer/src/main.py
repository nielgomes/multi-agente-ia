#indexer/src/main.py
import os
import json
import uuid
from flask import Flask, request, jsonify
from qdrant_client import QdrantClient, models
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from chunker_customizado import chunkificar_texto_completo

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
REGISTRY_DIR = '/app/registry'

try:
    client = QdrantClient(host='qdrant', port=6333)
    print("✅ Indexer: Conectado ao Qdrant com sucesso.")
except Exception as e:
    print(f"❌ Indexer: Falha ao conectar ao Qdrant: {e}")
    client = None

try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY não encontrada no ambiente.")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
    print("✅ Indexer: Modelo de embedding do Gemini carregado.")
except Exception as e:
    print(f"❌ Indexer: Falha ao carregar o modelo de embedding: {e}")
    embeddings = None

# --- FUNÇÕES AUXILIARES ---
def load_and_process_document(file_path: str) -> list[str]:
    # ... (esta função permanece a mesma)
    print(f"  -> Carregando o arquivo: {os.path.basename(file_path)}")
    if file_path.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    elif file_path.endswith(".txt"):
        loader = TextLoader(file_path, encoding='utf-8')
    else:
        print(f"   -> Formato de arquivo não suportado: {os.path.basename(file_path)}")
        return []
    document = loader.load()
    full_text = "\n".join([page.page_content for page in document])
    print(f"  -> Aplicando chunker customizado...")
    chunks = chunkificar_texto_completo(full_text)
    print(f"  -> Documento dividido em {len(chunks)} chunks.")
    return chunks

# --- ENDPOINTS DA API (AGORA COM SUPORTE A LOTES) ---

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
    for agent in agents_to_process:
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
            
            total_chunks = 0
            files_count = 0
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
            
            results.append({
                "agente": agent, "status": "sucesso", 
                "mensagem": f"Indexação concluída. {files_count} arquivos processados, {total_chunks} chunks adicionados."
            })
        except Exception as e:
            results.append({"agente": agent, "status": "erro", "mensagem": str(e)})

    return jsonify({"resumo_da_operacao": results})


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