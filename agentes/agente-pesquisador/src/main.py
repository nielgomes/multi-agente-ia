# agentes/agente-pesquisador/src/main.py
import os
import json
from qdrant_client import QdrantClient # <--- MUDANÇA: Importa o cliente do Qdrant
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from flask import Flask, request, jsonify

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
REGISTRY_DIR = '/app/registry'

# --- MUDANÇA: Configura o cliente para o Qdrant ---
try:
    client = QdrantClient(host='qdrant', port=6333)
    print("✅ Agente-Pesquisador: Conectado ao Qdrant com sucesso.")
except Exception as e:
    print(f"❌ Agente-Pesquisador: Falha ao conectar ao Qdrant: {e}")
    client = None

try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY não encontrada no ambiente.")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
    genai.configure(api_key=api_key)
    print("✅ Agente-Pesquisador: APIs do Gemini configuradas.")
except Exception as e:
    print(f"❌ Agente-Pesquisador: Falha na configuração das APIs: {e}")
    embeddings = None

def build_system_prompt_from_json(config: dict) -> str:
    # ... (Esta função não muda)
    instruction = config.get("system_instruction", {})
    rules_list = instruction.get("rules", [])
    rules_text = "\n".join(rules_list)
    full_prompt = f"""# Contexto\n{instruction.get("context", "")}\n\n# Objetivo Principal\n{instruction.get("goal", "")}\n\n# Regras\n{rules_text}"""
    return full_prompt.strip()

# --- ROTA PRINCIPAL (LÓGICA RAG ATUALIZADA PARA QDRANT) ---
@app.route("/executar", methods=["POST"])
def executar_tarefa():
    if not client or not embeddings:
        return jsonify({"erro": "Agente-Pesquisador não está pronto (Qdrant ou Embeddings falharam)."}), 503

    data = request.get_json()
    config_dir_name = data.get("config_dir_name")
    user_prompt = data.get("user_prompt")
    collection_name = f"colecao_{config_dir_name}"
    contexto = ""

    # PASSO 1: Busca no Qdrant
    try:
        # 1.1 Vetoriza a pergunta do usuário
        query_vector = embeddings.embed_query(user_prompt)
        
        # 1.2 Faz a busca por similaridade no Qdrant
        hits = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=5 # Pega os 5 resultados mais próximos
        )
        
        # 1.3 Extrai o texto do 'payload' dos resultados
        if hits:
            contexto = "\n\n".join([hit.payload['text'] for hit in hits])
            print(f"✅ Contexto recuperado da coleção '{collection_name}' no Qdrant.")
        else:
            print(f"⚠️ Nenhum documento relevante encontrado.")
    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível buscar na coleção '{collection_name}'. Erro: {e}")

    # O resto do fluxo (Passos 2, 3 e 4) permanece o mesmo
    try:
        config_path = os.path.join(REGISTRY_DIR, config_dir_name, 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        system_instruction = build_system_prompt_from_json(config)
        
        if contexto:
            final_prompt = f"""Use ESTRITAMENTE o contexto abaixo para responder a pergunta. Se a resposta não estiver no contexto, diga que não encontrou a informação na base de conhecimento.
Contexto:
---
{contexto}
---
Pergunta do Usuário: {user_prompt}
Resposta:"""
        else:
            final_prompt = user_prompt

        model = genai.GenerativeModel(
            model_name=config.get("persona", {}).get("model_name", "gemini-1.5-pro-latest"),
            system_instruction=system_instruction
        )
        response = model.generate_content(final_prompt)
        
        return jsonify({"resultado": response.text})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500