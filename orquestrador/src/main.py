#orquestrador/src/main.py
import os
import json
import requests
from flask import Flask, request, jsonify

# LangChain e Google Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
REGISTRY_DIR = '/app/registry'
agent_tools = []

# --- 1. FUNÇÕES DAS FERRAMENTAS ---
def call_agent_service(agent_name: str, task_description: str) -> str:
    """Função genérica para chamar qualquer um dos nossos microserviços de agentes."""
    print(f"🛠️  Delegando para o microserviço especialista: '{agent_name}'...")
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
    # ... (o corpo desta função permanece o mesmo)
    if not agent_tools: return "Nenhuma capacidade foi carregada ainda."
    descriptions = ["Olá! Eu sou um orquestrador de agentes de IA. Minhas capacidades vêm das ferramentas especialistas que eu coordeno:"]
    for tool in agent_tools:
        if tool.name != 'descrever_capacidades':
            descriptions.append(f"\n- **{tool.name.capitalize()}:** {tool.description}")
    return "\n".join(descriptions)

# --- 2. CARREGAMENTO DAS FERRAMENTAS ---
def load_tools():
    """Escaneia o registro e popula a lista de ferramentas para o AgentExecutor."""
    global agent_tools
    agent_tools = []
    print("🔎 Carregando ferramentas a partir do registro...")
    if os.path.isdir(REGISTRY_DIR):
        for agent_name in os.listdir(REGISTRY_DIR):
            config_path = os.path.join(REGISTRY_DIR, agent_name, 'config.json')
            if os.path.isfile(config_path):
                with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f)
                
                # --- Aqui é um exemplo de como customizar cada agente para usar o RAG Local, 
                # a ideia aqui é ser bem explicito sobre o que o agente responderá ---
                if agent_name == "pesquisador":
                    description = "Use esta ferramenta para responder a qualquer pergunta sobre a IA 'DanielGPT', sua data de criação, ou suas especialidades. Esta ferramenta tem acesso a uma base de conhecimento interna com informações factuais sobre este tópico."
                else:
                    description = config.get("persona", {}).get("description", "Nenhuma descrição.")
                
                tool = Tool(name=agent_name, func=lambda task, an=agent_name: call_agent_service(an, task), description=description)
                agent_tools.append(tool)
                print(f"  - Ferramenta de microserviço '{agent_name}' registrada.")
    
    agent_tools.append(Tool(
        name="descrever_capacidades",
        func=descrever_capacidades,
        description="Útil para responder perguntas sobre quem você é, o que você faz, ou quais são suas capacidades."
    ))
    print(f"✅ {len(agent_tools)} ferramentas carregadas no total.")

# --- 3. INICIALIZAÇÃO E CRIAÇÃO DO AGENTE ---
load_tools()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0,
    google_api_key=os.environ.get("GEMINI_API_KEY")
)

prompt = ChatPromptTemplate.from_messages([
    ("system", "Você é um orquestrador de agentes de IA. Sua função é analisar a solicitação do usuário e escolher a melhor ferramenta disponível para executar a tarefa. Delegue a tarefa para a ferramenta mais apropriada."),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_tool_calling_agent(llm, agent_tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=agent_tools, verbose=True)


# --- 4. ROTA DA API ---
@app.route("/iniciar-tarefa", methods=["POST"])
def iniciar_tarefa():
    data = request.get_json(); user_prompt = data.get("solicitacao")
    if not user_prompt: return jsonify({"erro": "O campo 'solicitacao' é obrigatório."}), 400
    try:
        result = agent_executor.invoke({"input": user_prompt})
        return jsonify({"resultado": result.get("output")})
    except Exception as e:
        return jsonify({"erro": f"Erro no executor do agente: {str(e)}"}), 500