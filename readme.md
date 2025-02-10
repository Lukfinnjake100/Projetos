## Setup

1. **Baixe o Docker e Postman**

Link do Docker:
https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe?utm_source=docker&utm_medium=webreferral&utm_campaign=docs-driven-download-win-amd64&_gl=1*14wjztm*_gcl_au*MTA4NTU0OTM2OC4xNzM5MDQ5MTQ1*_ga*NTE3NDM3MDgyLjE3MzkwNDkxNDU.*_ga_XJWPQMJYHQ*MTczOTE3NTQ2MC4zLjEuMTczOTE3NTQ4My4zNy4wLjA.

se voce estiver usando VScode, talvez você goste de utilizar a extensão do docker:
https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-docker

e outra extensão que vai ser inprescidivel é a do Redis, já que utilizamos Redis para essa aplicação:
https://marketplace.visualstudio.com/items?itemName=Redis.redis-for-vscode

utilizei a versão portátil do postman para fazer os testes:
https://portapps.io/app/postman-portable/

2. **Baixe o Python**

utilizei a versão 3.12.2 de 04/02/2025
https://www.python.org/ftp/python/3.13.2/python-3.13.2-amd64.exe

**configuração padrão, marque as caixas do PATH na instalação e após tudo isso, reinicie a máquina**

3. **Execute Redis Container**:
   docker run -d --name redis-container -p 6379:6379 redis

4. **Create Docker-Compose.yml**:

#Criar um arquivo chamado "docker-compose.yml" e colar a configuração

version: "3.9"

services:
redis:
image: redis
container_name: redis-container
ports: - "6379:6379"

api:
build: .
container_name: fastapi-container
ports: - "8000:8000"
depends_on: - redis
environment: - REDIS_HOST=redis

5. **Create Dockerfile**:

# Criar um arquvio "Dockerfile" e colar as linhas abaixo

# Base image com Python slim

FROM python:3.9-slim

# Definir o diretório de trabalho

WORKDIR /app

# Copiar os arquivos do projeto para o container

COPY . .

# Instalar dependências

RUN pip install --no-cache-dir fastapi uvicorn redis

# Comando para rodar a aplicação

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

6. **Install dependencies**:

   ```sh
   pip install fastapi uvicorn redis
   ```

7. **Run the application**:

   ```sh
   python -m uvicorn main:app --reload --log-level info
   ```

## Endpoints

- **GET /**: Returns a welcome message.

## Example

To test the application, run the following command and navigate to `http://127.0.0.1:8000` in your browser:

to see doc swagger: `http://127.0.0.1:8000/docs`

```sh
uvicorn main:app --reload

```

## Postman collection

Postman collection on root folder ./redis.postman_collection.json
