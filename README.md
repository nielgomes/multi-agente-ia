## Como Usar os Endpoints para Indexar

    Um agente especifico:
    JSON
```
// POST http://localhost:5005/indexar
{
    "agente": "pesquisador"
}
```
Um ou mais agentes específicos:
JSON
```
// POST http://localhost:5005/indexar
{
    "agentes": ["pesquisador", "codificador"]
}
```
Todos os agentes:
JSON
```
    // POST http://localhost:5005/indexar
    {
        "agente": "*"
    }
```
Para Apagar

    Um agente específico:
    JSON
```
// DELETE http://localhost:5005/apagar
{
    "agente": "pesquisador"
}
```
Um ou mais agentes específicos:
JSON
```
// DELETE http://localhost:5005/apagar
{
    "agentes": ["pesquisador", "codificador"]
}
```
Todos os agentes:
JSON
```
// DELETE http://localhost:5005/apagar
{
    "agente": "*"
}
```

Atualmente nosso indexer suporta nativamente arquivos `.txt` e `.pdf`.

## Endpoints de chamadas para interação:

* Geral:

`http://localhost:5000/iniciar-tarefa`

* Shopee:

`http://localhost:5000/gerar_roteiro_shopee`

### Histórico de contexto

O projeto Multi-Agente é pronto para tratar com interações que mantenham histório, formanto do json é:

* Interação inicial (sem histórico):

```
{
    "solicitacao": "Quais os modelos do GPT tem na openrouter?",
    "historico_chat": []
}
```
* Interação com historico
```
	{
    "solicitacao": "Quais os modelos do GPT tem na openrouter?",
    "historico_chat": [
        {
            "role": "user",
            "content": "Usando a api da openrouter, me informe qual o modelo estamos usando?"
        },
        {
            "role": "ai",
            "content": "Estamos usando uma versão do **ChatGPT baseada na arquitetura GPT‑4**."
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
* Json de Resposta:
```
{
	"resultado": "A OpenRouter oferece uma vasta gama de modelos da família GPT (desenvolvidos pela OpenAI). Aqui estão os principais, agrupados por categoria e com (...)"
}
```
## Novos agentes

Sempre que incluir novos agentes, além de criar as pastas dele em **/agentes** e em **/registry**, lembre se de mapear uma porta para o serviço no arquivo **orquestrador/src/main.py** na função **call_agent_service** em **port_mapping**

### orquestrador/src/quais_modelos.py

O arquivo `quais_modelos.py` é um script utilitário para o desenvolvedor. A sua única função é ajudá-lo a descobrir quais nomes de modelos da API da Gemini (models/gemini-2.5-pro, models/embedding-001, etc.) estão disponíveis para a chave de API da Google. Você o executa manualmente no seu terminal para obter uma lista de modelos válidos que pode depois copiar e colar no campo `model_name`: dos seus ficheiros `config.json`. Ele não é chamado por nenhum outro serviço e não toma nenhuma decisão.

### Arquivo registry/`agente escolhido`/knowledge_base/youtube.txt

Na pasta `knowledge_base` de cada agente dentro da pasta `registry` pode receber um arquivo com o nome de `youtube.txt`, nele você pode informar uma ou mais URLs do Youtube em linhas diferentes (uma URL por linha de texto). Ao detectar esse arquivo na pasta o modulo Indexer acionará o Gemini para ele fazer um resumo dos vídeos de cada um das URLs de forma individual e indexará no indice RAG do respectivo agente.