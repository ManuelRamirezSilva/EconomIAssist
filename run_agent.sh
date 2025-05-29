#!/bin/bash

echo "🚀 Iniciando EconomIAssist..."

# Cargar NVM y configurar Node.js 18
if [ -s "$HOME/.nvm/nvm.sh" ]; then
    source "$HOME/.nvm/nvm.sh"
    nvm use 18 >/dev/null 2>&1
fi

# Activar entorno virtual
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Ejecutar el agente
python src/agent/conversational_agent.py
