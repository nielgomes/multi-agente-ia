import google.generativeai as genai
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
# Isso permite que o script encontre sua chave de API.
load_dotenv()

try:
    # Pega a chave de API do ambiente
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Chave de API do Gemini não encontrada. Verifique seu arquivo .env")

    # Configura a biblioteca com sua chave
    genai.configure(api_key=api_key)

    print("✅ Autenticação bem-sucedida. Buscando modelos disponíveis...\n")

    # Itera sobre todos os modelos retornados pela API
    for model in genai.list_models():
        # A string 'generateContent' no nome do método é o que procuramos.
        # Isso filtra para apenas os modelos que podem gerar texto (chat, etc.).
        if 'generateContent' in model.supported_generation_methods:
            print(f"▶️ Nome do Modelo: {model.name}")

except Exception as e:
    print(f"❌ Ocorreu um erro: {e}")