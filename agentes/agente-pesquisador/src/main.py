import os
import json
from qdrant_client import QdrantClient
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from flask import Flask, request, jsonify

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
REGISTRY_DIR = '/app/registry'

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
    """Função auxiliar para montar a instrução de sistema a partir do config.json."""
    instruction = config.get("system_instruction", {})
    rules_list = instruction.get("rules", [])
    rules_text = "\n".join(rules_list)
    full_prompt = f"""# Contexto\n{instruction.get("context", "")}\n\n# Objetivo Principal\n{instruction.get("goal", "")}\n\n# Regras\n{rules_text}"""
    return full_prompt.strip()

# --- ROTA PRINCIPAL ---
@app.route("/executar", methods=["POST"])
def executar_tarefa():
    if not client or not embeddings:
        return jsonify({"erro": "Agente-Pesquisador não está pronto."}), 503

    try:
        data = request.get_json()
        config_dir_name = data.get("config_dir_name")
        user_prompt = data.get("user_prompt")
        collection_name = f"colecao_{config_dir_name}"
        contexto = ""

        # PASSO 1: Busca no Qdrant
        try:
            query_vector = embeddings.embed_query(user_prompt)
            hits = client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=5
            )
            if hits:
                contexto = "\n\n".join([hit.payload['text'] for hit in hits])
                print(f"✅ Contexto recuperado da coleção '{collection_name}' no Qdrant.")
            else:
                print(f"⚠️ Nenhum documento relevante encontrado.")
        except Exception as e:
            print(f"⚠️ Aviso: Não foi possível buscar na coleção '{collection_name}'. Erro: {e}")

        # PASSO 2: Carrega a configuração e monta o prompt
        config_path = os.path.join(REGISTRY_DIR, config_dir_name, 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # --- CORREÇÃO APLICADA AQUI ---
        # 2.1 - Garante que a instrução de sistema seja construída
        system_instruction = build_system_prompt_from_json(config)
        
        # 2.2 - Carrega o template do prompt RAG do config
        rag_prompt_template = config.get("rag_prompt_template", "Contexto: {contexto}\n\nPergunta: {user_prompt}\n\nResposta:")
        
        if contexto:
            final_prompt = rag_prompt_template.format(contexto=contexto, user_prompt=user_prompt)
        else:
            final_prompt = user_prompt

        # PASSO 3: Chama o Gemini
        model = genai.GenerativeModel(
            model_name=config.get("persona", {}).get("model_name", "gemini-1.5-pro-latest"),
            system_instruction=system_instruction # Agora a variável existe
        )
        response = model.generate_content(final_prompt)
        
        return jsonify({"resultado": response.text})

    except Exception as e:
        print(f"❌ Erro Crítico no Agente-Pesquisador: {e}")
        return jsonify({"erro": str(e)}), 500