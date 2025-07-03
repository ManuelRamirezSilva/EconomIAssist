#!/bin/bash
# Script para testing rápido del WhatsApp simulator

echo "🤖 EconomIAssist WhatsApp Testing Suite"
echo "======================================="

# Verificar si el servidor está corriendo
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Servidor WhatsApp está corriendo"
else
    echo "❌ Servidor no está corriendo"
    echo "💡 Ejecuta en otra terminal: python src/whatsapp/whatsapp_server.py"
    exit 1
fi

echo ""
echo "Opciones disponibles:"
echo "1. Modo interactivo (simple)"
echo "2. Test de conversación predefinida"
echo "3. Enviar mensaje único"
echo "4. Modo interactivo avanzado (async)"

read -p "Selecciona una opción (1-4): " option

case $option in
    1)
        echo "🔄 Iniciando modo interactivo simple..."
        python tests/simple_whatsapp_test.py
        ;;
    2)
        echo "🧪 Ejecutando test de conversación..."
        python tests/simple_whatsapp_test.py test
        ;;
    3)
        read -p "Escribe tu mensaje: " message
        echo "📨 Enviando mensaje..."
        python tests/simple_whatsapp_test.py single "$message"
        ;;
    4)
        echo "🔄 Iniciando modo interactivo avanzado..."
        python tests/whatsapp_simulator.py --interactive
        ;;
    *)
        echo "❌ Opción inválida"
        exit 1
        ;;
esac
