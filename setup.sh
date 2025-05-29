#!/bin/bash

# EconomIAssist - Setup Script Completo
echo "🚀 Configurando EconomIAssist..."

# Función para verificar si Docker está instalado
check_docker() {
    if command -v docker &> /dev/null; then
        echo "✅ Docker está instalado"
        return 0
    else
        echo "❌ Docker no está instalado"
        return 1
    fi
}

# Función para instalar Docker en Ubuntu/Debian
install_docker_ubuntu() {
    echo "📦 Instalando Docker en Ubuntu/Debian..."
    
    # Actualizar repositorios
    sudo apt-get update
    
    # Instalar dependencias
    sudo apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Agregar clave GPG oficial de Docker
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Agregar repositorio
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Instalar Docker Engine
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Agregar usuario al grupo docker
    sudo usermod -aG docker $USER
    
    echo "✅ Docker instalado. Es necesario reiniciar la sesión o ejecutar 'newgrp docker'"
    return 0
}

# Función para instalar Docker en otras distribuciones
install_docker_other() {
    echo "📦 Para otras distribuciones, instala Docker manualmente:"
    echo "   🔗 https://docs.docker.com/engine/install/"
    echo "   📋 Comandos comunes:"
    echo "      - Fedora: sudo dnf install docker-ce docker-ce-cli containerd.io"
    echo "      - Arch: sudo pacman -S docker"
    echo "      - openSUSE: sudo zypper install docker"
    echo ""
    echo "⚠️ Después de instalar, ejecuta este script nuevamente"
    return 1
}

# Verificar sistema operativo
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        echo "❌ No se pudo detectar el sistema operativo"
        return 1
    fi
}

# Verificar e instalar Docker si es necesario
setup_docker() {
    if check_docker; then
        # Verificar que Docker esté ejecutándose
        if sudo docker info &> /dev/null; then
            echo "✅ Docker está funcionando correctamente"
        else
            echo "🔄 Iniciando servicio Docker..."
            sudo systemctl start docker
            sudo systemctl enable docker
        fi
    else
        echo "🐳 Docker es necesario para el servidor de base de conocimiento"
        read -p "¿Deseas instalar Docker automáticamente? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            detect_os
            if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
                install_docker_ubuntu
            else
                install_docker_other
                return 1
            fi
        else
            echo "⚠️ Docker no instalado. El agente funcionará sin memoria persistente."
            echo "💡 Para funcionalidad completa, instala Docker manualmente:"
            echo "   🔗 https://docs.docker.com/engine/install/"
            return 1
        fi
    fi
    return 0
}

# Verificar Node.js para Tavily MCP
check_nodejs() {
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        echo "✅ Node.js está instalado: $NODE_VERSION"
        
        # Verificar si la versión es 18 o superior
        NODE_MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1 | sed 's/v//')
        if [ "$NODE_MAJOR" -ge 18 ]; then
            echo "✅ Versión de Node.js es compatible (18+)"
        else
            echo "⚠️ Se recomienda Node.js 18+. Versión actual: $NODE_VERSION"
        fi
    else
        echo "❌ Node.js no está instalado"
        echo "📦 Para búsqueda web, instala Node.js:"
        echo "   🔗 https://nodejs.org/"
        echo "   📋 O usa un gestor de versiones como nvm:"
        echo "      curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"
        echo "      source ~/.bashrc"
        echo "      nvm install 18"
    fi
}

# ====== INICIO DEL SCRIPT PRINCIPAL ======

echo "🔍 Verificando dependencias del sistema..."

# 1. Verificar Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ Python está instalado: $PYTHON_VERSION"
else
    echo "❌ Python3 no está instalado. Instálalo primero."
    exit 1
fi

# 2. Verificar y configurar Docker
setup_docker
DOCKER_AVAILABLE=$?

# 3. Verificar Node.js
check_nodejs

echo ""
echo "🐍 Configurando entorno Python..."

# Crear entorno virtual si no existe
if [ ! -d ".venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv .venv
fi

# Activar entorno virtual
echo "🔧 Activando entorno virtual..."
source .venv/bin/activate

# Instalar dependencias
echo "📥 Instalando dependencias Python..."
pip install --upgrade pip
pip install -r requirements.txt

# Verificar archivo .env
echo ""
echo "🔑 Verificando configuración..."
if [ ! -f ".env" ]; then
    echo "⚠️ Archivo .env no encontrado"
    echo "📝 Crea un archivo .env con las siguientes variables:"
    echo "   AZURE_OPENAI_API_BASE=tu_endpoint"
    echo "   AZURE_OPENAI_API_KEY=tu_api_key"
    echo "   AZURE_OPENAI_API_VERSION=2024-12-01-preview"
    echo "   AZURE_OPENAI_DEPLOYMENT_NAME=tu_deployment"
    echo "   TAVILY_API_KEY=tu_tavily_key (opcional)"
else
    echo "✅ Archivo .env encontrado"
fi

# Preparar volumen Docker si está disponible
if [ $DOCKER_AVAILABLE -eq 0 ]; then
    echo ""
    echo "🗄️ Preparando base de conocimiento..."
    
    # Verificar si el volumen existe
    if docker volume ls | grep -q knowledgebase; then
        echo "✅ Volumen 'knowledgebase' ya existe"
    else
        echo "📦 Creando volumen 'knowledgebase'..."
        docker volume create knowledgebase
    fi
    
    # Descargar imagen de KnowledgeBase
    echo "⬇️ Descargando imagen del servidor de base de conocimiento..."
    docker pull mbcrawfo/knowledge-base-server
fi

echo ""
echo "🎉 ¡EconomIAssist configurado exitosamente!"
echo ""
echo "📋 Resumen de configuración:"
echo "   🐍 Python: ✅"
echo "   🐳 Docker: $([ $DOCKER_AVAILABLE -eq 0 ] && echo "✅" || echo "❌")"
echo "   🌐 Node.js: $(command -v node &> /dev/null && echo "✅" || echo "❌")"
echo "   🔑 Configuración: $([ -f ".env" ] && echo "✅" || echo "⚠️")"
echo ""
echo "🚀 Para probar el agente:"
echo "   python tests/run_all_tests.py"
echo ""
echo "🎯 Para usar el agente directamente:"
echo "   python src/agent/conversational_agent.py"

if [ $DOCKER_AVAILABLE -ne 0 ]; then
    echo ""
    echo "💡 Nota: Sin Docker, el agente funcionará con funcionalidad limitada"
    echo "   (sin memoria persistente). Para funcionalidad completa,"
    echo "   instala Docker y ejecuta este script nuevamente."
fi
