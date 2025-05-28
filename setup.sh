#!/bin/bash

# EconomIAssist - Setup Script Simplificado
echo "🚀 Configurando EconomIAssist..."

# Crear entorno virtual si no existe
if [ ! -d ".venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv .venv
fi

# Activar entorno virtual
echo "🔧 Activando entorno virtual..."
source .venv/bin/activate

# Instalar dependencias
echo "📥 Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

# Verificar archivo .env
if [ ! -f ".env" ]; then
    echo "⚠️ Archivo .env no encontrado. Crea uno basado en el ejemplo."
    echo "Necesitas configurar las API keys de Azure OpenAI y Tavily."
else
    echo "✅ Archivo .env encontrado"
fi

echo "🎉 ¡EconomIAssist configurado exitosamente!"
echo "Para usar el agente, ejecuta: python -m tests.run_all_tests"
