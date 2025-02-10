#!/bin/bash

# Nome do repositório no GitHub
REPO_NAME="Projetos"
SUBFOLDER_NAME="API Methods"
USUARIO="Lukfinnjake100"

# Verificar se o repositório Git já está inicializado
if [ ! -d ".git" ]; then
    echo "Inicializando repositório Git..."
    git init
else
    echo "Repositório Git já inicializado."
fi

# Adicionar todos os arquivos ao repositório
echo "Adicionando arquivos ao repositório..."
git add .

# Criar commit inicial
echo "Criando commit inicial..."
git commit -m "Initial commit"

# Criar subpasta e mover arquivos
echo "Criando subpasta e movendo arquivos..."
mkdir -p "$SUBFOLDER_NAME"
git mv * "$SUBFOLDER_NAME"

# Criar commit das mudanças
echo "Criando commit das mudanças..."
git add .
git commit -m "Move project files to $SUBFOLDER_NAME subfolder"

# Adicionar repositório remoto
echo "Adicionando repositório remoto..."
git remote add origin "https://github.com/$USUARIO/$REPO_NAME.git"

# Enviar arquivos para o GitHub
echo "Enviando arquivos para o GitHub..."
git push -u origin master

echo "Processo concluído!"