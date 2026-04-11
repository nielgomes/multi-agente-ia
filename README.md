# Projeto Multi-Agente 🤖

## 📋 Visão Geral

O **Projeto Multi-Agente** é uma arquitetura de microserviços baseada em agentes de IA que trabalha em conjunto para executar diferentes tarefas de forma especializada e coordenada. O sistema utiliza o padrão de **Orquestrador de Agentes**, onde um agente principal coordena a delegação de tarefas para agentes especialistas, cada um com sua área de expertise.

### 🏗️ Arquitetura do Sistema

O projeto é composto por múltiplos microserviços Docker, cada um representando um agente especializado:

| Agente | Porta | Função |
|--------|-------|--------|
| **Orquestrador** | 5000 | Coordena e delega tarefas para os agentes especializados |
| **Agente-Pesquisador** | 5001 | Realiza pesquisas utilizando base de conhecimento vectorizada (RAG) |
| **Agente-Escritor** | 5002 | Criação, revisão e otimização de textos e conteúdo |
| **Agente-Codificador** | 5003 | Tarefas relacionadas a código e programação |
| **Agente-Shopee** | 5004 | Gera roteiros para vídeos de afiliados da Shopee |
| **Agente-OpenRouter** | 5006 | Gateway para modelos de IA via OpenRouter |
| **Indexer** | 5005 | Indexa documentos e arquivos na base de conhecimento vectorial |
| **Qdrant** | 6333 | Banco de dados vetorial para busca semântica |

### 🎯 Objetivos do Projeto

1. **Especialização**: Cada agente é especializado em uma tarefa específica
2. **Escalabilidade**: Arquitetura de microserviços permite escalar individualmente
3. **Flexibilidade**: Novas ferramentas podem ser adicionadas facilmente
4. **Base de Conhecimento**: Utiliza RAG (Retrieval-Augmented Generation) para respostas precisas
5. **Coordenação Inteligente**: O orquestrador decide qual agente usar baseado na solicitação

---

## 🚀 Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- **Docker** (versão 20.10 ou superior)
- **Docker Compose** (versão 1.29 ou superior)
- **Git** (para clonar o repositório)

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
# API do Google Gemini (obrigatória para a maioria dos agentes)
GEMINI_API_KEY=sua_chave_aqui

# API do OpenRouter (para modelos alternativos)
OPENROUTER_API_KEY=sua_chave_aqui

# Credenciais da Shopee (para o agente de afiliados)
SHOPEE_USER=seu_email@email.com
SHOPEE_PASS=sua_senha

# Credenciais Google (opcional, para algumas funcionalidades)
GOOGLE_EMAIL=seu_email@gmail.com
GOOGLE_PASSWORD=sua_senha

# API do ScraperAPI (opcional, para scraping)
SCRAPERAPI_KEY=sua_chave_aqui

# Token Bearer (opcional)
BEARER_TOKEN=seu_token_aqui
```

---

## 📦 Instalação

### 1. Clone o Repositório

```bash
git clone https://github.com/seu-repositorio/projeto-multi-agente.git
cd projeto-multi-agente
```

### 2. Configure as Variáveis de Ambiente

```bash
cp .env.example .env
# Edite o arquivo .env com suas chaves de API
```

### 3. Construa as Imagens Docker

```bash
# Constrói todas as imagens de uma vez
docker-compose build
```

Ou construa individualmente:

```bash
# Orquestrador
docker build -f orquestrador/Dockerfile -t orquestrador:latest .

# Agente Pesquisador
docker build -f agentes/agente-pesquisador/Dockerfile -t agente-pesquisador:latest .

# Agente Escritor
docker build -f agentes/agente-escritor/Dockerfile -t agente-escritor:latest .

# Agente Codificador
docker build -f agentes/agente-codificador/Dockerfile -t agente-codificador:latest .

# Agente Shopee
docker build -f agentes/agente-shopee/Dockerfile -t agente-shopee:latest .

# Agente OpenRouter
docker build -f agentes/agente-openrouter/Dockerfile -t agente-openrouter:latest .

# Indexer
docker build -f indexer/Dockerfile -t indexer:latest .
```

---

## ▶️ Como Subir os Containers

### Iniciar Todos os Serviços

```bash
# Inicia todos os containers em segundo plano
docker-compose up -d
```

### Verificar Status dos Containers

```bash
docker-compose ps
```

### Logs em Tempo Real

```bash
# Ver logs de todos os serviços
docker-compose logs -f

# Ver logs de um serviço específico
docker-compose logs -f orquestrador
docker-compose logs -f agente-pesquisador
docker-compose logs -f indexer
docker-compose logs -f qdrant
```

### Parar os Containers

```bash
# Para todos os containers
docker-compose down

# Para e remove volumes (cuidado: apaga os dados do Qdrant)
docker-compose down -v
```

---

## 🔧 Como Usar a API

### Endpoint Principal - Orquestrador

**URL Base:** `http://localhost:5000`

#### Iniciar uma Tarefa

```
POST http://localhost:5000/iniciar-tarefa
```

**Requisição (sem histórico):**
```json
{
  "solicitacao": "Quais os modelos do GPT tem na openrouter?",
  "historico_chat": []
}
```

**Requisição (com histórico):**
```json
{
  "solicitacao": "Quais os modelos do GPT tem na openrouter?",
  "historico_chat": [
    {
      "role": "user",
      "content": "Usando a api da openrouter, me informe qual o modelo estamos usando?"
    },
    {
      "role": "ai",
      "content": "Estamos usando uma versão do ChatGPT baseada na arquitetura GPT-4."
    },
    {
      "role": "user",
      "content": "Ja é o GPT-oss?"
    },
    {
      "role": "ai",
      "content": "Sim, openai/gpt-oss-20b:free"
    }
  ]
}
```

**Resposta:**
```json
{
  "resultado": "Resposta gerada pelo agente..."
}
```

---

## 📚 Indexação de Conhecimento

O sistema utiliza o **Qdrant** como banco de dados vetorial para busca semântica. Cada agente possui uma pasta `knowledge_base` no diretório `registry/[agente]/knowledge_base/` onde você pode adicionar documentos.

### Formatos Suportados

- `.txt` - Arquivos de texto
- `.pdf` - Documentos PDF
- `.docx` - Documentos Word
- `.csv` - Arquivos CSV
- `.xml` - Arquivos XML

### Endpoints de Indexação

**URL Base do Indexer:** `http://localhost:5005`

#### Indexar Um Agente Específico

```
POST http://localhost:5005/indexar
```

```json
{
  "agente": "pesquisador"
}
```

#### Indexar Múltiplos Agentes

```json
{
  "agentes": ["pesquisador", "codificador"]
}
```

#### Indexar Todos os Agentes
Atualmente nosso indexer suporta nativamente arquivos `.docx`, `.csv`, `.txt` e `.pdf`.

```json
{
  "agente": "*"
}
```

#### Apagar Índice de Um Agente

```
DELETE http://localhost:5005/apagar
```

```json
{
  "agente": "pesquisador"
}
```

#### Apagar Múltiplos Agentes

```json
{
  "agentes": ["pesquisador", "codificador"]
}
```

#### Apagar Todos os Agentes

```json
{
  "agente": "*"
}
```

---

## 🛠️ Agentes Disponíveis

### 1. Orquestrador (Porta 5000)

O agente principal que coordena todos os outros. Utiliza **LangChain** para gerenciar ferramentas e executar tarefas.

**Características:**
- Usa Google Gemini 2.5 Pro
- Coordena automaticamente o agente correto para cada tarefa
- Suporta histórico de chat para conversas contextuais

### 2. Agente-Pesquisador (Porta 5001)

Especialista em pesquisa com base de conhecimento vectorizada.

**Características:**
- Busca semântica no Qdrant
- Prioriza fontes confiáveis
- Sempre cita as fontes utilizadas

### 3. Agente-Escritor (Porta 5002)

Especialista em criação e edição de conteúdo textual.

**Funcionalidades:**
- Criação de artigos
- Revisão e otimização de textos
- Resumos e reescritas

### 4. Agente-Codificador (Porta 5003)

Especialista em programação e código.

**Funcionalidades:**
- Geração de código
- Revisão de código
- Explicações técnicas

### 5. Agente-Shopee (Porta 5004)

Especialista em criação de roteiros para vídeos de afiliados da Shopee.

**Entrada Esperada:**
```json
{
  "source_url": "https://shopee.com.br/produto...",
  "title": "Nome do Produto",
  "description": "Descrição do produto"
}
```

**Saída:** Roteiro otimizado para Reels/TikTok com link de afiliado.

### 6. Agente-OpenRouter (Porta 5006)

Gateway para modelos de IA via OpenRouter.

**Modelos Suportados:**
- meta-llama/llama-3-70b-instruct
- openai/gpt-4
- E muitos outros via OpenRouter

---

## 📊 Monitoramento e Logs

### Verificar Status dos Serviços

```bash
# Verificar se todos os serviços estão rodando
docker-compose ps

# Verificar recursos utilizados
docker stats
```

### Acessar o Qdrant (Dashboard)

O Qdrant possui um dashboard visual disponível em:

```
http://localhost:6333/dashboard
```

---

## 🔨 Desenvolvimento

### Estrutura de Arquivos

```
projeto-multi-agente/
├── agentes/                    # Agentes especializados
│   ├── agente-codificador/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── src/main.py
│   ├── agente-escritor/
│   ├── agente-openrouter/
│   ├── agente-pesquisador/
│   └── agente-shopee/
├── indexer/                    # Serviço de indexação
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py
│       ├── chunker_customizado.py
│       ├── refatorador_rag.py
│       └── prompt.json
├── orquestrador/               # Agente orquestrador
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py
│       └── quais_modelos.py
├── registry/                   # Configurações e knowledge bases
│   ├── codificador/
│   │   └── config.json
│   ├── escritor/
│   │   ├── config.json
│   │   └── knowledge_base/
│   ├── openrouter/
│   │   ├── config.json
│   │   └── knowledge_base/
│   ├── orquestrador/
│   │   └── config.json
│   ├── pesquisador/
│   │   ├── config.json
│   │   └── knowledge_base/
│   └── shopee/
│       ├── config.json
│       └── knowledge_base/
├── docker-compose.yml
├── .env
└── README.md
```

### Adicionar Novo Agente

1. Crie uma nova pasta em `agentes/`
2. Adicione `Dockerfile` e `requirements.txt`
3. Crie a pasta `src/main.py` com o endpoint `/executar`
4. Adicione a configuração em `registry/[nome-do-agente]/config.json`
5. Adicione o serviço no `docker-compose.yml`
6. Mapeie a porta no arquivo `orquestrador/src/main.py` na função `call_agent_service`

### Arquivo `quais_modelos.py`

O arquivo `orquestrador/src/quais_modelos.py` é um script utilitário para o desenvolvedor. A sua única função é ajudá-lo a descobrir quais nomes de modelos da API da Gemini (models/gemini-2.5-pro, models/embedding-001, etc.) estão disponíveis para a chave de API da Google.

Você o executa manualmente no seu terminal para obter uma lista de modelos válidos que pode depois copiar e colar no campo `model_name` dos seus ficheiros `config.json`. Ele não é chamado por nenhum outro serviço e não toma nenhuma decisão.

### Arquivo `youtube.txt`

Na pasta `knowledge_base` de cada agente dentro da pasta `registry` pode receber um arquivo com o nome de `youtube.txt`, nele você pode informar uma ou mais URLs do Youtube em linhas diferentes (uma URL por linha de texto).

Ao detectar esse arquivo na pasta, o módulo Indexer acionará o Gemini para ele fazer um resumo dos vídeos de cada uma das URLs de forma individual e indexará no índice RAG do respective agente.

---

## ⚠️ Troubleshooting

### Problema: Agente não conecta ao Qdrant

```bash
# Verifique se o container do Qdrant está rodando
docker-compose ps qdrant

# Verifique os logs
docker-compose logs qdrant
```

### Problema: Erro de API Key

Certifique-se de que a `GEMINI_API_KEY` está configurada corretamente no arquivo `.env`.

### Problema: Container não inicia

```bash
# Rebuild completo
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 📄 Licença

Este projeto está sob a licença MIT.

---

## 👤 Autor

Desenvolvido por Niel Gomes
Na pasta `knowledge_base` de cada agente dentro da pasta `registry` pode receber um arquivo com o nome de `youtube.txt`, nele você pode informar uma ou mais URLs do Youtube em linhas diferentes (uma URL por linha de texto). Ao detectar esse arquivo na pasta o modulo Indexer acionará o Gemini para ele fazer um resumo dos vídeos de cada um das URLs de forma individual e indexará no indice RAG do respectivo agente.
