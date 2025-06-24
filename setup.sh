#!/bin/bash

# ================================================================
# EconomIAssist - Script de Configuración Completa
# ================================================================
# Configura automáticamente todas las dependencias del proyecto
# Incluye: Python, Docker, Node.js, Google Calendar, MCP servers

echo "🚀 Configurando EconomIAssist - Agente Conversacional Económico..."
echo "================================================================"

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
        # Verificar que Docker esté ejecutándose (intentar múltiples sockets)
        if docker info &> /dev/null; then
            echo "✅ Docker está funcionando correctamente"
        elif sudo docker info &> /dev/null; then
            echo "✅ Docker está funcionando correctamente (requiere sudo)"
        else
            echo "🔄 Iniciando servicio Docker..."
            sudo systemctl start docker
            sudo systemctl enable docker
            # Verificar nuevamente
            if docker info &> /dev/null || sudo docker info &> /dev/null; then
                echo "✅ Docker iniciado correctamente"
            else
                echo "❌ Error al iniciar Docker. Verifica manualmente."
                return 1
            fi
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

# Verificar Node.js para MCP servers (Tavily, Google Calendar)
check_nodejs() {
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        echo "✅ Node.js está instalado: $NODE_VERSION"
        
        # Verificar si la versión es 18 o superior
        NODE_MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1 | sed 's/v//')
        if [ "$NODE_MAJOR" -ge 18 ]; then
            echo "✅ Versión de Node.js es compatible (18+)"
            return 0
        else
            echo "⚠️ Se recomienda Node.js 18+. Versión actual: $NODE_VERSION"
            return 1
        fi
    else
        echo "❌ Node.js no está instalado"
        echo "📦 Node.js es NECESARIO para Google Calendar y Tavily"
        echo "🔗 Instalando Node.js automáticamente..."
        install_nodejs
        return $?
    fi
}

# Instalar Node.js automáticamente
install_nodejs() {
    echo "📦 Instalando Node.js..."
    
    # Instalar nvm (Node Version Manager)
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
    
    # Recargar perfil para usar nvm
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
    
    # Instalar Node.js LTS
    nvm install --lts
    nvm use --lts
    nvm alias default node
    
    echo "✅ Node.js instalado exitosamente"
    return 0
}

# Instalar dependencias MCP vía npm
install_mcp_servers() {
    echo ""
    echo "📦 Instalando servidores MCP..."
    
    # Verificar npm
    if ! command -v npm &> /dev/null; then
        echo "❌ npm no está disponible"
        return 1
    fi
    
    # Inicializar package.json si no existe
    if [ ! -f "package.json" ]; then
        echo "📦 Inicializando proyecto Node.js..."
        npm init -y > /dev/null 2>&1
    fi
    
    # Instalar dependencias localmente usando package.json
    echo "🔧 Instalando dependencias MCP via npm..."
    if npm install; then
        echo "✅ Dependencias MCP instaladas localmente"
    else
        echo "⚠️ Algunos paquetes npm pueden no estar disponibles"
    fi
    
    # Instalar calculadora MCP vía pip
    echo "🔧 Instalando Calculator MCP..."
    pip install mcp-server-calculator
    
    echo "✅ Servidores MCP instalados"
    return 0
}

# Verificar credenciales de Google
check_google_credentials() {
    echo ""
    echo "🔑 Verificando credenciales de Google Calendar..."
    
    if [ -f "config/gcp-service-account.json" ]; then
        echo "✅ Archivo de credenciales encontrado: config/gcp-service-account.json"
        
        # Verificar estructura básica del archivo JSON
        if python3 -c "import json; json.load(open('config/gcp-service-account.json'))" 2>/dev/null; then
            echo "✅ Formato JSON válido"
            
            # Verificar que sea una cuenta de servicio
            SERVICE_TYPE=$(python3 -c "import json; print(json.load(open('config/gcp-service-account.json')).get('type', ''))" 2>/dev/null)
            if [ "$SERVICE_TYPE" = "service_account" ]; then
                echo "✅ Cuenta de servicio válida"
            else
                echo "⚠️ El archivo no parece ser una cuenta de servicio"
            fi
        else
            echo "❌ Archivo JSON inválido"
        fi
    else
        echo "⚠️ No se encontró config/gcp-service-account.json"
        echo "📝 Para Google Calendar, necesitas:"
        echo "   1. Crear un proyecto en Google Cloud Console"
        echo "   2. Habilitar Google Calendar API"
        echo "   3. Crear una cuenta de servicio"
        echo "   4. Descargar las credenciales como gcp-service-account.json"
        echo "   📚 Guía completa: docs/google_calendar_setup.md"
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

# 3. Verificar y configurar Node.js
check_nodejs
NODEJS_AVAILABLE=$?

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
    
    # Función helper para ejecutar docker con o sin sudo
    run_docker() {
        if docker "$@" 2>/dev/null; then
            return 0
        elif sudo docker "$@" 2>/dev/null; then
            return 0
        else
            return 1
        fi
    }
    
    # Verificar si el volumen existe
    if run_docker volume ls | grep -q knowledgebase; then
        echo "✅ Volumen 'knowledgebase' ya existe"
    else
        echo "📦 Creando volumen 'knowledgebase'..."
        if run_docker volume create knowledgebase; then
            echo "✅ Volumen creado exitosamente"
        else
            echo "❌ Error creando volumen Docker"
        fi
    fi
    
    # Descargar imagen de KnowledgeBase
    echo "⬇️ Descargando imagen del servidor de base de conocimiento..."
    if run_docker pull mbcrawfo/knowledge-base-server; then
        echo "✅ Imagen descargada exitosamente"
    else
        echo "⚠️ Error descargando imagen Docker"
    fi
fi

# Instalar servidores MCP
if [ $NODEJS_AVAILABLE -eq 0 ]; then
    install_mcp_servers
else
    echo "⚠️ Node.js no disponible - algunos servidores MCP no se instalarán"
fi

# Verificar credenciales de Google
check_google_credentials

echo ""
echo "🎉 ¡EconomIAssist configurado exitosamente!"
echo ""
echo "📋 Resumen de configuración:"
echo "   🐍 Python: ✅"
echo "   🐳 Docker: $([ $DOCKER_AVAILABLE -eq 0 ] && echo "✅" || echo "❌")"
echo "   🌐 Node.js: $([ $NODEJS_AVAILABLE -eq 0 ] && echo "✅" || echo "❌")"
echo "   🔑 Configuración: $([ -f ".env" ] && echo "✅" || echo "⚠️")"
echo "   📅 Google Calendar: $([ -f "config/gcp-service-account.json" ] && echo "✅" || echo "⚠️")"
echo ""
echo "🚀 Para probar el agente:"
echo "   source .venv/bin/activate"
echo "   python src/agent/conversational_agent.py"
echo ""
echo "🧪 Para ejecutar tests:"
echo "   python tests/run_all_tests.py"

if [ $NODEJS_AVAILABLE -ne 0 ]; then
    echo ""
    echo "💡 Nota: Sin Node.js, Google Calendar y Tavily no funcionarán"
    echo "   Instala Node.js 18+ y ejecuta este script nuevamente."
fi
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