#agentes/agente-shopee/src/main.py
import os
import json
import google.generativeai as genai
from flask import Flask, request, jsonify

# --- CONFIGURAÇÃO ---
app = Flask(__name__)
REGISTRY_DIR = '/app/registry'
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
# Sua tag de afiliado. Pode ser movida para o .env no futuro.
AFFILIATE_TAG = "seucodigo-123" 

# --- FUNÇÕES AUXILIARES ---
def build_system_prompt_from_json(config: dict) -> str:
    instruction = config.get("system_instruction", {})
    rules_list = instruction.get("rules", [])
    roles_text = "\n".join(rules_list)
    full_prompt = f"""# Contexto\n{instruction.get("context", "")}\n\n# Objetivo Principal\n{instruction.get("goal", "")}\n\n# Regras\n{roles_text}"""
    return full_prompt.strip()

def convert_to_affiliate_link(original_url: str) -> str:
    """Adiciona a tag de afiliado a uma URL da Shopee."""
    # Lógica simples, pode ser aprimorada
    separator = '&' if '?' in original_url else '?'
    return f"{original_url}{separator}af_id={AFFILIATE_TAG}&utm_source=an&utm_medium=affiliates&utm_campaign=default_campaign"

# --- ROTA DA API ---
@app.route("/executar", methods=["POST"])
def executar_tarefa():
    try:
        data = request.get_json()
        # Espera receber os dados de forma estruturada do orquestrador
        source_url = data.get("source_url")
        title = data.get("title")
        description = data.get("description")

        if not all([source_url, title, description]):
            return jsonify({"erro": "Os campos 'source_url', 'title' e 'description' são obrigatórios."}), 400

        config_path = os.path.join(REGISTRY_DIR, "shopee", 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        system_instruction = build_system_prompt_from_json(config)
        affiliate_link = convert_to_affiliate_link(source_url)

        # Monta o prompt final para o Gemini com os dados recebidos
        final_prompt = f"""
Dados Brutos do Produto:
- Título: {title}
- Descrição: {description}
- Link de Afiliado (use este no CTA): {affiliate_link}

Com base estritamente nos dados acima, crie o roteiro para o vídeo.
"""
        
        model = genai.GenerativeModel(
            model_name=config.get("persona", {}).get("model_name", "gemini-2.5-pro"),
            system_instruction=system_instruction,
            generation_config={"temperature": config.get("persona", {}).get("temperature", 0.8)}
        )
        response = model.generate_content(final_prompt)
        
        return jsonify({"resultado": response.text})

    except Exception as e:
        return jsonify({"erro": f"Erro no agente Shopee: {str(e)}"}), 500