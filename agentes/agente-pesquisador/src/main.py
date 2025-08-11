# agentes/agente-pesquisador/src/main.py
import os
import json
import chromadb
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from flask import Flask, request, jsonify

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
REGISTRY_DIR = '/app/registry'
client = chromadb.HttpClient(host='chromadb', port=8000)
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=os.environ.get("GEMINI_API_KEY"))
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def build_system_prompt_from_json(config: dict) -> str:
    instruction = config.get("system_instruction", {})
    rules_list = instruction.get("rules", [])
    rules_text = "\n".join(rules_list)
    full_prompt = f"""# Contexto\n{instruction.get("context", "")}\n\n# Objetivo Principal\n{instruction.get("goal", "")}\n\n# Regras\n{rules_text}"""
    return full_prompt.strip()

# --- ROTA PRINCIPAL ---
@app.route("/executar", methods=["POST"])
def executar_tarefa():
    try:
        data = request.get_json()
        config_dir_name = data.get("config_dir_name")
        user_prompt = data.get("user_prompt")
        collection_name = f"colecao_{config_dir_name}"
        contexto = ""

        # PASSO 1: Tenta buscar na base de conhecimento. É a fonte primária.
        try:
            collection = client.get_collection(name=collection_name)
            results = collection.query(query_texts=[user_prompt], n_results=3)
            if results and results['documents'] and results['documents'][0]:
                contexto = "\n\n".join(results['documents'][0])
                print(f"✅ Contexto recuperado da coleção '{collection_name}'.")
            else:
                print(f"⚠️ Nenhum documento relevante encontrado.")
        except Exception as e:
            print(f"⚠️ Aviso: Não foi possível buscar na coleção '{collection_name}'. Erro: {e}")

        # PASSO 2: Carrega a personalidade do agente
        config_path = os.path.join(REGISTRY_DIR, config_dir_name, 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        system_instruction = build_system_prompt_from_json(config)
        
        # PASSO 3: Monta o prompt final (com ou sem contexto)
        if contexto:
            # Se TEMOS contexto do RAG, forçamos o modelo a usá-lo
            final_prompt = f"""Use ESTRITAMENTE o contexto abaixo para responder a pergunta. Se a resposta não estiver no contexto, diga que não encontrou a informação na base de conhecimento.
Contexto:
---
{contexto}
---
Pergunta do Usuário: {user_prompt}
Resposta:"""
        else:
            # Se NÃO TEMOS contexto, o agente age com seu conhecimento geral
            final_prompt = user_prompt

        # PASSO 4: Chama o Gemini
        model = genai.GenerativeModel(
            model_name=config.get("persona", {}).get("model_name", "gemini-1.5-pro-latest"),
            system_instruction=system_instruction
        )
        response = model.generate_content(final_prompt)
        
        return jsonify({"resultado": response.text})

    except Exception as e:
        print(f"❌ Erro Crítico no Agente-Pesquisador: {e}")
        return jsonify({"erro": str(e)}), 500