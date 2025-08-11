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