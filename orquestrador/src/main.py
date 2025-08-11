#orquestrador/src/main.py
import os
import json
import requests
from qdrant_client import QdrantClient
from flask import Flask, request, jsonify

# LangChain e Google Imports
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
import google.generativeai as genai

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
REGISTRY_DIR = '/app/registry'
agent_tools = []

# Configura as APIs e Clientes
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY não encontrada no ambiente.")
    
    genai.configure(api_key=api_key)
    # Conecta ao serviço 'qdrant' definido no docker-compose.yml
    client = QdrantClient(host='qdrant', port=6333)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
    print("✅ Orquestrador: Conectado ao Qdrant e API do Gemini configurada.")

except Exception as e:
    print(f"❌ Erro crítico na inicialização: {e}")
    client = None
    embeddings = None

# --- LÓGICA DO AGENT EXECUTOR (PARA /iniciar-tarefa) ---

def call_agent_service(agent_name: str, task_description: str) -> str:
    """Função genérica para chamar qualquer um dos nossos microserviços de agentes."""
    port_mapping = {"pesquisador": 5001, "escritor": 5002, "codificador": 5003, "shopee": 5004}
    agent_port = port_mapping.get(agent_name)
    if not agent_port: return f"Erro: Agente '{agent_name}' desconhecido."
    
    agent_url = f"http://agente-{agent_name}:{agent_port}/executar"
    payload = {"config_dir_name": agent_name, "user_prompt": task_description}
    
    try:
        response = requests.post(agent_url, json=payload, timeout=180)
        response.raise_for_status()
        return response.json().get("resultado", "O agente não retornou um resultado.")
    except requests.exceptions.RequestException as e:
        return f"Erro de comunicação com o agente '{agent_name}': {e}"

def descrever_capacidades(task_description: str) -> str:
    """Função local que descreve as capacidades do agente."""
    if not agent_tools: return "Nenhuma capacidade foi carregada ainda."
    descriptions = ["Olá! Eu sou um orquestrador de agentes de IA. Minhas capacidades vêm das ferramentas especialistas que eu coordeno:"]
    for tool in agent_tools:
        if tool.name != 'descrever_capacidades':
            descriptions.append(f"\n- **{tool.name.capitalize()}:** {tool.description}")
    return "\n".join(descriptions)

def load_tools():
    """Escaneia o registro e popula a lista de ferramentas para o AgentExecutor."""
    global agent_tools
    agent_tools = []
    if os.path.isdir(REGISTRY_DIR):
        for agent_name in os.listdir(REGISTRY_DIR):
            config_path = os.path.join(REGISTRY_DIR, agent_name, 'config.json')
            if os.path.isfile(config_path):
                with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f)
                description = config.get("persona", {}).get("description", "Nenhuma descrição.")
                tool = Tool(name=agent_name, func=lambda task, an=agent_name: call_agent_service(an, task), description=description)
                agent_tools.append(tool)
    
    agent_tools.append(Tool(
        name="descrever_capacidades",
        func=descrever_capacidades,
        description="Útil para responder perguntas sobre quem você é, o que você faz, ou quais são suas capacidades."
    ))

load_tools()

llm_agent = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0,
    google_api_key=os.environ.get("GEMINI_API_KEY")
)
prompt_agent = ChatPromptTemplate.from_messages([
    ("system", "Você é um orquestrador de agentes de IA. Sua função é analisar a solicitação do usuário e escolher a melhor ferramenta disponível para executar a tarefa. Delegue a tarefa para a ferramenta mais apropriada."),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])
agent = create_tool_calling_agent(llm_agent, agent_tools, prompt_agent)
agent_executor = AgentExecutor(agent=agent, tools=agent_tools, verbose=True)


# --- ROTAS DA API ---

@app.route("/iniciar-tarefa", methods=["POST"])
def iniciar_tarefa():
    """Endpoint para tarefas complexas que exigem escolha de ferramentas."""
    data = request.get_json()
    user_prompt = data.get("solicitacao")
    if not user_prompt: return jsonify({"erro": "O campo 'solicitacao' é obrigatório."}), 400
    try:
        result = agent_executor.invoke({"input": user_prompt})
        return jsonify({"resultado": result.get("output")})
    except Exception as e:
        return jsonify({"erro": f"Erro no executor do agente: {str(e)}"}), 500

@app.route("/responder-com-rag", methods=["POST"])
def responder_com_rag():
    """Endpoint otimizado para respostas diretas da base de conhecimento usando Qdrant."""
    if not client or not embeddings:
        return jsonify({"erro": "Serviço de RAG não está pronto (Qdrant ou Embeddings falharam)."}), 503
        
    data = request.get_json()
    user_prompt = data.get("solicitacao")
    agent_name_para_rag = data.get("agente", "pesquisador")
    if not user_prompt:
        return jsonify({"erro": "O campo 'solicitacao' é obrigatório."}), 400

    print(f"--- ROTA RAG DIRETA ACIONADA PARA O AGENTE '{agent_name_para_rag}' ---")
    
    contexto = ""
    collection_name = f"colecao_{agent_name_para_rag}"
    try:
        # 1. Vetoriza a pergunta do usuário usando o modelo do Google
        query_vector = embeddings.embed_query(user_prompt)
        
        # 2. Faz a busca por similaridade no Qdrant
        hits = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=5 # Pega os 5 resultados mais próximos
        )
        
        # O resultado do Qdrant (hits) contém o 'payload' com nosso texto
        if hits:
            contexto = "\n\n".join([hit.payload['text'] for hit in hits])
            print(f"✅ Contexto recuperado da coleção '{collection_name}' no Qdrant.")

    except Exception as e:
        return jsonify({"erro": f"Não foi possível consultar a base de conhecimento do agente '{agent_name_para_rag}'. Erro: {e}"}), 500

    if not contexto:
        contexto = "Nenhuma informação relevante encontrada na base de conhecimento."

    final_prompt = f"""Você é um assistente de Resposta a Perguntas. Sua tarefa é responder à "Pergunta do Usuário" baseando-se ESTRITAMENTE E EXCLUSIVAMENTE nas informações fornecidas no "Contexto da Base de Conhecimento". Não utilize nenhum conhecimento externo. Se a resposta não estiver no contexto, responda exatamente: "A informação solicitada não foi encontrada na minha base de conhecimento."

Contexto da Base de Conhecimento:
---
{contexto}
---

Pergunta do Usuário: {user_prompt}

Resposta:
"""
    try:
        model = genai.GenerativeModel(model_name="gemini-2.5-pro")
        response = model.generate_content(final_prompt)
        print("✅ Resposta gerada com sucesso pelo Gemini usando RAG.")
        return jsonify({"resultado": response.text})
    except Exception as e:
        return jsonify({"erro": f"Erro ao chamar o modelo Gemini: {str(e)}"}), 500