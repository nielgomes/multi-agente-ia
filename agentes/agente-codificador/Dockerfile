# 1. Imagem Base
FROM python:3.10-slim

# 2. Declara o argumento de build AQUI (depois do FROM)
#    Agora ele estará disponível para os comandos seguintes.
ARG SERVICE_PATH

# 3. Diretório de Trabalho
WORKDIR /app

# 4. Copia de Dependências
#    Usa o argumento para construir o caminho dinamicamente.
COPY ${SERVICE_PATH}/requirements.txt .

# 5. Instalação de Dependências
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copia do Código Fonte
#    Usa o argumento para construir o caminho dinamicamente.
COPY ${SERVICE_PATH}/src .

# 7. Copia do Registry
COPY ./registry ./registry

# 8. Comando de Execução
CMD ["flask", "run", "--host=0.0.0.0"]