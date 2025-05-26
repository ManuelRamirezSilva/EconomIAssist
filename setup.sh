#!/bin/bash
# setup.sh - Instalación automática de dependencias Python y Node.js para EconomIAssist
set -e

# Instalar dependencias Python
if [ -f requirements.txt ]; then
    echo "📦 Instalando dependencias Python..."
    pip install -r requirements.txt
else
    echo "⚠️ No se encontró requirements.txt"
fi

# Instalar dependencias Node.js (tavily-mcp)
if command -v npm >/dev/null 2>&1; then
    echo "📦 Instalando tavily-mcp (Node.js)..."
    npm install -g tavily-mcp
else
    echo "❌ npm no está instalado. Por favor instala Node.js (https://nodejs.org/) y vuelve a ejecutar este script."
    exit 1
fi

echo "✅ Setup completo."
