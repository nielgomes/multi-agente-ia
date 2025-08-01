# agentes/agente-codificador/src/main.pyS
import os
import json
import google.generativeai as genai
from flask import Flask, request, jsonify

# Configuração inicial
app = Flask(__name__)
try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
except AttributeError:
    print("ERRO: GEMINI_API_KEY não encontrada.")
    exit()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_DIR = os.path.join(BASE_DIR, 'registry')


def build_system_prompt_from_json(config: dict) -> str:
    """
    Constrói uma única string de 'system_instruction' a partir de um JSON estruturado.
    """
    # Pega as seções principais do JSON
    persona = config.get("persona", {})
    instruction = config.get("system_instruction", {})
    tone = config.get("tone_of_voice", "")
    output_format = config.get("output_format", "")

    # Monta a lista de papéis/regras
    roles_list = instruction.get("roles", [])
    roles_text = "\n".join(roles_list)

    # Concatena todas as partes em um único prompt Markdown
    # Usar Markdown ajuda o modelo a entender melhor a estrutura.
    full_prompt = f"""
# PERSONA
**Título:** {persona.get("title", "")}
**Nome:** {persona.get("name", "")}
**Descrição:** {persona.get("description", "")}

# INSTRUÇÕES DO SISTEMA
## Contexto
{instruction.get("context", "")}

## Objetivo Principal
{instruction.get("goal", "")}

## Regras e Papéis
{roles_text}

# TOM DE VOZ
{tone}

# FORMATO DE SAÍDA OBRIGATÓRIO
{output_format}
"""
    return full_prompt


@app.route("/executar", methods=["POST"])
def executar_tarefa():
    """
    Endpoint genérico que executa uma tarefa baseada em um arquivo de configuração.
    """
    data = request.get_json()
    config_dir_name = data.get("config_dir_name")
    user_prompt = data.get("user_prompt")

    if not config_dir_name or not user_prompt:
        return jsonify({"erro": "Campos 'config_dir_name' e 'user_prompt' são obrigatórios"}), 400

    config_path = os.path.join(REGISTRY_DIR, config_dir_name, 'config.json')

    try:
        # 1. Carrega a configuração do agente a partir do arquivo JSON
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        persona_title = config.get("persona", {}).get("title", "Desconhecida")
        print(f"Personalidade '{persona_title}' carregada.")

        # 2. Constrói o prompt do sistema dinamicamente
        system_prompt = build_system_prompt_from_json(config)
        
        # 3. Carrega arquivos da base de conhecimento (lógica mantida)
        uploaded_files = []
        kb_dir_path = os.path.join(REGISTRY_DIR, config_dir_name, config.get("knowledge_base_dir", ""))
        
        if os.path.exists(kb_dir_path) and os.path.isdir(kb_dir_path):
            # AINDA VAMOS IMPLEMENTAR A LÓGICA DE UPLOAD AQUI.
            # USAMOS 'PASS' PARA EVITAR O ERRO DE SINTAXE.
            pass
        
        # 4. Configura o modelo dinamicamente
        model_name = config.get("persona", {}).get("model_name", "gemini-1.5-flash")
        temperature = config.get("persona", {}).get("temperature", 0.7)
        
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt,
            generation_config={"temperature": temperature}
        )

        # 5. Executa o prompt
        prompt_content = [user_prompt] + uploaded_files
        response = model.generate_content(prompt_content)
        
        # ... (lógica para deletar arquivos permanece a mesma)

        return jsonify({"resultado": response.text})

    except FileNotFoundError:
        return jsonify({"erro": f"Arquivo de configuração não encontrado em: {config_path}"}), 404
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port)