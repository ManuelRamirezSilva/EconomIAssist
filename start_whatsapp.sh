#!/bin/bash

# ================================================================
# Script de inicio coordinado para EconomIAssist + WhatsApp
# ================================================================

echo "🚀 Iniciando EconomIAssist con integración WhatsApp"
echo "================================================================"

# Variables para PIDs
ECONOMI_ASSIST_PID=""
WHATSAPP_BRIDGE_PID=""

# Función para manejar la limpieza al salir
cleanup() {
    echo ""
    echo "🛑 Cerrando todos los servicios..."
    
    # Matar procesos en background
    if [ ! -z "$ECONOMI_ASSIST_PID" ]; then
        kill $ECONOMI_ASSIST_PID 2>/dev/null
        echo "✅ Servidor EconomIAssist cerrado"
    fi
    
    if [ ! -z "$WHATSAPP_BRIDGE_PID" ]; then
        kill $WHATSAPP_BRIDGE_PID 2>/dev/null
        echo "✅ WhatsApp Bridge cerrado"
    fi
    
    # Matar cualquier proceso en puerto 8000
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    
    echo "👋 ¡Hasta luego!"
    exit 0
}

# Configurar trap para limpieza
trap cleanup SIGINT SIGTERM EXIT

# Verificar dependencias
echo "🔍 Verificando dependencias..."

# Verificar Python y entorno virtual
if [ ! -d ".venv" ]; then
    echo "❌ Entorno virtual no encontrado. Ejecuta './setup.sh' primero."
    exit 1
fi

# Verificar Node.js para WhatsApp Bridge
if ! command -v node &> /dev/null; then
    echo "❌ Node.js no está instalado. Se necesita para WhatsApp Bridge."
    exit 1
fi

# Verificar que el WhatsApp Bridge esté configurado
if [ ! -f "whatsapp-simple/package.json" ]; then
    echo "❌ WhatsApp Bridge no encontrado en whatsapp-simple/"
    exit 1
fi

# Verificar dependencias de Node.js
cd whatsapp-simple
if [ ! -d "node_modules" ]; then
    echo "📦 Instalando dependencias de WhatsApp Bridge..."
    npm install
fi
cd ..

echo "✅ Dependencias verificadas"

# Activar entorno virtual de Python
echo "🐍 Activando entorno virtual Python..."
source .venv/bin/activate

# Verificar que no haya nada ejecutándose en puerto 8000
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️ Puerto 8000 ocupado. Liberando..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo ""
echo "🔥 Iniciando servicios..."

# 1. Iniciar servidor HTTP de EconomIAssist
echo "📡 Iniciando servidor EconomIAssist en puerto 8000..."

# Cambiar al directorio correcto y ejecutar en background
cd src/whatsapp
export PYTHONPATH="$PWD/../..:$PYTHONPATH"
python whatsapp_server.py > ../../logs/whatsapp_server.log 2>&1 &
ECONOMI_ASSIST_PID=$!
cd ../..

echo "🔄 Esperando a que el servidor se inicialice..."

# Esperar hasta 30 segundos para que el servidor responda
TIMEOUT=30
COUNT=0
while [ $COUNT -lt $TIMEOUT ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Servidor EconomIAssist funcionando en http://localhost:8000"
        break
    fi
    
    if ! kill -0 $ECONOMI_ASSIST_PID 2>/dev/null; then
        echo "❌ El proceso del servidor murió. Revisa logs/whatsapp_server.log"
        exit 1
    fi
    
    sleep 1
    COUNT=$((COUNT + 1))
    echo -n "."
done
echo ""

if [ $COUNT -eq $TIMEOUT ]; then
    echo "❌ Error: Servidor EconomIAssist no responde después de ${TIMEOUT}s"
    echo "📋 Revisa el log en logs/whatsapp_server.log"
    exit 1
fi

# 2. Iniciar WhatsApp Bridge
echo "📱 Iniciando WhatsApp Bridge..."
cd whatsapp-simple
node whatsapp-bridge.js &
WHATSAPP_BRIDGE_PID=$!
cd ..

echo ""
echo "🎉 ¡Ambos servicios iniciados exitosamente!"
echo ""
echo "📋 Estado de servicios:"
echo "   🤖 EconomIAssist Server: http://localhost:8000 (PID: $ECONOMI_ASSIST_PID)"
echo "   📱 WhatsApp Bridge: Iniciando... (PID: $WHATSAPP_BRIDGE_PID)"
echo ""
echo "📱 INSTRUCCIONES:"
echo "   1. Busca el código QR en la salida del WhatsApp Bridge"
echo "   2. Escanéalo con WhatsApp en tu teléfono"
echo "   3. ¡Listo! Ya puedes enviar mensajes a EconomIAssist por WhatsApp"
echo ""
echo "🔍 Para verificar el estado:"
echo "   - EconomIAssist: curl http://localhost:8000/health"
echo "   - Logs: tail -f logs/whatsapp_server.log"
echo ""
echo "🛑 Para detener: Ctrl+C"
echo ""

# Mostrar logs del servidor en tiempo real
echo "📋 Logs del servidor EconomIAssist:"
tail -f logs/whatsapp_server.log &
TAIL_PID=$!

# Esperar a que ambos procesos terminen o que el usuario presione Ctrl+C
wait $ECONOMI_ASSIST_PID $WHATSAPP_BRIDGE_PID