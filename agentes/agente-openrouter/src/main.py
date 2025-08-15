#agentes/agente-openrouter/src/main.py
import os
import json
from flask import Flask, request, jsonify

# Importamos a classe base da OpenAI, que é a mais estável
from langchain_openai import ChatOpenAI

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
REGISTRY_DIR = '/app/registry'

# --- ROTA PRINCIPAL ---
@app.route("/executar", methods=["POST"])
def executar_tarefa():
    try:
        data = request.get_json()
        config_dir_name = data.get("config_dir_name")
        user_prompt = data.get("user_prompt")

        if not config_dir_name or not user_prompt:
            return jsonify({"erro": "Campos obrigatórios ausentes."}), 400

        config_path = os.path.join(REGISTRY_DIR, config_dir_name, 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        model_name = config.get("persona", {}).get("model_name", "meta-llama/llama-3-70b-instruct")
        temperature = config.get("persona", {}).get("temperature", 0.7)
        
        # --- LÓGICA DE CONEXÃO CORRIGIDA E ROBUSTA ---
        # Instanciamos a classe ChatOpenAI, mas apontamos para a API do OpenRouter
        chat = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            openai_api_base="https://openrouter.ai/api/v1", # URL Base do OpenRouter
            openai_api_key=os.environ.get("OPENROUTER_API_KEY")
        )
        
        response = chat.invoke(user_prompt)
        
        return jsonify({"resultado": response.content})

    except Exception as e:
        return jsonify({"erro": f"Erro no agente OpenRouter: {str(e)}"}), 500