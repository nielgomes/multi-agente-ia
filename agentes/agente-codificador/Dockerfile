# Declara o argumento de build que será recebido do docker-compose.yml
ARG SERVICE_PATH

# Imagem Base
FROM python:3.10-slim

# Declara o argumento DEPOIS do FROM para torná-lo disponível
ARG SERVICE_PATH

# Diretório de Trabalho
WORKDIR /app

# Copia de Dependências
COPY ${SERVICE_PATH}/requirements.txt .

# Instalação de Dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia do Código Fonte
COPY ${SERVICE_PATH}/src .

# Copia do Registry
COPY ./registry ./registry

# --- MUDANÇA CRUCIAL AQUI ---
# Comando de Execução robusto que não depende do $PATH
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]