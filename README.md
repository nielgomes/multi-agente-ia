## Como Usar os Endpoints:

Agora você tem muito mais flexibilidade.

## Para Indexar

    Um agente:
    JSON
```
// POST http://localhost:5005/indexar
{
    "agente": "pesquisador"
}
```
Agentes específicos:
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

    Um agente:
    JSON
```
// DELETE http://localhost:5005/apagar
{
    "agente": "pesquisador"
}
```
Agentes específicos:
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

# Novos agentes

Sempre que incluir novos agentes, além de criar as pastas dele em **/agentes** e em **/registry**, lembre se de mapear uma porta para o serviço no arquivo **orquestrador/src/main.py** na função **call_agent_service** em **port_mapping**

### orquestrador/src/quais_modelos.py

O arquivo `quais_modelos.py` é um script utilitário para o desenvolvedor. A sua única função é ajudá-lo a descobrir quais nomes de modelos da API da Gemini (models/gemini-1.5-pro-latest, models/embedding-001, etc.) estão disponíveis para a chave de API da Google. Você o executa manualmente no seu terminal para obter uma lista de modelos válidos que pode depois copiar e colar no campo `model_name`: dos seus ficheiros `config.json`. Ele não é chamado por nenhum outro serviço e não toma nenhuma decisão.