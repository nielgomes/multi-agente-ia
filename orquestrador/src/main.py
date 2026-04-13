#orquestrador/src/main.py
import os
import json
import requests
from flask import Flask, request, jsonify

# LangChain e Google Imports (updated for new LangChain API)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage
from typing import Type

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
REGISTRY_DIR = '/app/registry'
agent_tools = []

# Carrega a configuração do próprio orquestrador na inicialização
with open(os.path.join(REGISTRY_DIR, 'orquestrador', 'config.json'), 'r', encoding='utf-8') as f:
    orquestrador_config = json.load(f)

# --- 1. FUNÇÕES DAS FERRAMENTAS ---
def call_agent_service(agent_name: str, task_description: str) -> str:
    """Função genérica para chamar qualquer um dos nossos microserviços de agentes."""
    print(f"🛠️  Delegando para o microserviço especialista: '{agent_name}'...")
    port_mapping = {"pesquisador": 5001,
                     "escritor": 5002,
                     "codificador": 5003,
                     "shopee": 5004,
                     "openrouter": 5006}
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

# --- NOVA FUNÇÃO WRAPPER PARA O AGENTE SHOPEE ---
def shopee_tool_wrapper(title: str, description: str, source_url: str) -> str:
    """
    Chama o microserviço do agente Shopee com os dados estruturados
    extraídos da solicitação do usuário.
    """
    print("🛠️  Delegando para o 'agente-shopee' com dados estruturados...")
    agent_url = f"http://agente-shopee:5004/executar"
    payload = {"source_url": source_url, "title": title, "description": description}
    try:
        response = requests.post(agent_url, json=payload, timeout=180)
        response.raise_for_status()
        return response.json().get("resultado", "O agente Shopee não retornou um resultado.")
    except requests.exceptions.RequestException as e:
        return f"Erro de comunicação com o agente Shopee: {e}"

def descrever_capacidades(task_description: str) -> str:
    print("🛠️  Executando ferramenta local 'descrever_capacidades'...")
    if not agent_tools: return "Nenhuma capacidade foi carregada ainda."
    # Carrega o texto de introdução do config.json
    intro_text = orquestrador_config.get("tools", {}).get("descrever_capacidades", {}).get("intro_text", "")
    descriptions = [intro_text]
    for tool in agent_tools:
        if tool.name != 'descrever_capacidades':
            descriptions.append(f"\n- **{tool.name.capitalize()}:** {tool.description}")
    return "\n".join(descriptions)

# --- 2. CARREGAMENTO DAS FERRAMENTAS ---
def load_tools():
    global agent_tools
    agent_tools = []
    print("🔎 Carregando ferramentas a partir do registro...")
    if os.path.isdir(REGISTRY_DIR):
        for agent_name in os.listdir(REGISTRY_DIR):
            if agent_name == 'orquestrador': continue
            
            config_path = os.path.join(REGISTRY_DIR, agent_name, 'config.json')
            if not os.path.isfile(config_path): continue
                
            with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f)
            description = config.get("persona", {}).get("langchain_tool_description", "Nenhuma descrição.")
            
            # Lógica especial para a ferramenta Shopee
            if agent_name == "shopee":
                shopee_tool = Tool(
                    name="shopee",
                    func=shopee_tool_wrapper,
                    description=description
                )
                agent_tools.append(shopee_tool)
                print(f"  - Ferramenta ESTRUTURADA '{agent_name}' registrada.")
            else: # Lógica para todas as outras ferramentas
                tool = Tool(name=agent_name, func=lambda task, an=agent_name: call_agent_service(an, task), description=description)
                agent_tools.append(tool)
                print(f"  - Ferramenta de microserviço '{agent_name}' registrada.")
    
    # Adiciona a ferramenta de autodescrição, lendo sua descrição do config.json
    desc_tool_description = orquestrador_config.get("tools", {}).get("descrever_capacidades", {}).get("description", "")
    agent_tools.append(Tool(
        name="descrever_capacidades",
        func=descrever_capacidades,
        description=desc_tool_description
    ))
    print(f"✅ {len(agent_tools)} ferramentas carregadas no total.")

# --- INICIALIZAÇÃO E CRIAÇÃO DO AGENTE ---
load_tools()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0,
    google_api_key=os.environ.get("GEMINI_API_KEY")
)

# Carrega o system_prompt do config.json
system_prompt = orquestrador_config.get("system_prompt", "Você é um assistente prestativo.")

# Cria o agente usando a nova API do LangChain
agent_executor = create_agent(
    model=llm,
    tools=agent_tools,
    system_prompt=system_prompt
)


# --- 4. ROTA DA API ---
@app.route("/iniciar-tarefa", methods=["POST"])
def iniciar_tarefa():
    data = request.get_json()
    user_prompt = data.get("solicitacao")
    # A rota agora aceita um histórico opcional
    chat_history_raw = data.get("historico_chat", []) 
    
    if not user_prompt: return jsonify({"erro": "O campo 'solicitacao' é obrigatório."}), 400

    # Converte o histórico JSON em objetos que o LangChain entende
    chat_history = []
    for msg in chat_history_raw:
        if msg.get("role") == "user":
            chat_history.append(HumanMessage(content=msg.get("content")))
        elif msg.get("role") == "ai":
            chat_history.append(AIMessage(content=msg.get("content")))

    try:
        # Passamos o histórico para o executor
        # Usando a nova API do LangChain agent
        result = agent_executor.invoke({
            "messages": [HumanMessage(content=user_prompt)] + chat_history
        })
        
        # Extrai a resposta final
        final_response = result["messages"][-1].content if result.get("messages") else "Desculpe, não consegui processar sua solicitação."
        return jsonify({"resultado": final_response})
    except Exception as e:
        return jsonify({"erro": f"Erro no executor do agente: {str(e)}"}), 500