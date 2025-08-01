import os
import json
import re
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from flask import Flask, request, jsonify

# --- CONFIGURAÇÃO ---
app = Flask(__name__)
try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
except AttributeError:
    print("ERRO: GEMINI_API_KEY não encontrada.")
    exit()

REGISTRY_DIR = '/app/registry'

# --- FUNÇÕES DE LÓGICA ---

def scrape_url_content(url: str) -> str:
    """
    Usa requests e BeautifulSoup para extrair o conteúdo de texto de uma URL.
    """
    try:
        print(f"🔎 Acessando a URL: {url}")
        # Headers para simular um navegador e evitar bloqueios simples
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Lança erro para status ruins (4xx, 5xx)

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extrai o texto do corpo da página e limpa espaços excessivos
        body_text = soup.body.get_text(separator=' ', strip=True)
        print(f"✅ Conteúdo extraído com sucesso ({len(body_text)} caracteres).")
        return body_text
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao acessar a URL: {e}")
        return f"Erro ao acessar a URL: {e}"

def find_url_in_prompt(prompt: str) -> str | None:
    """Encontra a primeira URL HTTP ou HTTPS no texto do prompt."""
    # Expressão regular para encontrar URLs
    url_pattern = re.compile(r'https?://\S+')
    match = url_pattern.search(prompt)
    return match.group(0) if match else None


def build_system_prompt_from_json(config: dict) -> str:
    # ... (Esta função continua exatamente a mesma que tínhamos antes)
    persona = config.get("persona", {})
    instruction = config.get("system_instruction", {})
    tone = config.get("tone_of_voice", "")
    output_format = config.get("output_format", "")
    roles_list = instruction.get("roles", [])
    roles_text = "\n".join(roles_list)
    full_prompt = f"""
# PERSONA
**Título:** {persona.get("title", "")}
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

# --- ROTA DA API ---
@app.route("/executar", methods=["POST"])
def executar_tarefa():
    data = request.get_json()
    config_dir_name = data.get("config_dir_name")
    user_prompt = data.get("user_prompt")

    if not config_dir_name or not user_prompt:
        return jsonify({"erro": "Campos obrigatórios ausentes."}), 400

    try:
        # --- LÓGICA DE SCRAPING ADICIONADA ---
        page_content = "Nenhum conteúdo de página foi extraído."
        url = find_url_in_prompt(user_prompt)
        if url:
            page_content = scrape_url_content(url)
        else:
            print("Nenhuma URL encontrada no prompt.")

        # Monta um novo prompt para o Gemini com o conteúdo extraído
        final_user_prompt = f"""
A tarefa solicitada pelo usuário é: '{user_prompt}'

Para te ajudar a completar esta tarefa, aqui está o conteúdo de texto extraído da URL fornecida:
---
{page_content}
---
Por favor, use o conteúdo acima para executar a tarefa solicitada.
"""
        # --- FIM DA LÓGICA DE SCRAPING ---

        config_path = os.path.join(REGISTRY_DIR, config_dir_name, 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        persona_title = config.get("persona", {}).get("title", "Desconhecida")
        print(f"Personalidade '{persona_title}' carregada para processar os dados.")

        system_prompt = build_system_prompt_from_json(config)
        
        model_name = config.get("persona", {}).get("model_name", "gemini-1.5-flash")
        temperature = config.get("persona", {}).get("temperature", 0.7)
        
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt,
            generation_config={"temperature": temperature}
        )

        response = model.generate_content(final_user_prompt)
        
        return jsonify({"resultado": response.text})

    except Exception as e:
        return jsonify({"erro": str(e)}), 500