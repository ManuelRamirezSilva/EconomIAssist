#!/usr/bin/env python3
"""
Test script para el agente EconomIAssist simplificado
Demuestra la facilidad de uso del SDK nativo de OpenAI con MCP
"""

import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.openai_agent_simple import EconomIAssistAgent, run_agent

async def test_basic_functionality():
    """Prueba básica del agente simplificado."""
    print("🧪 Probando EconomIAssist - Versión Simplificada")
    print("=" * 60)
    
    # Test queries financieras
    test_messages = [
        "¿Cuáles son los principales tipos de inversión?",
        "Dame consejos para ahorrar dinero mensualmente",
        "¿Cómo puedo calcular mi presupuesto personal?",
        "¿Cuál es la tasa de interés actual en Argentina?",  # Esta debería usar fetch
    ]
    
    agent = EconomIAssistAgent()
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n📝 Test {i}: {message}")
        print("-" * 40)
        
        try:
            response = await agent.chat(message)
            print(f"🤖 Respuesta: {response[:200]}...")  # Primeros 200 chars
            print("✅ Test exitoso")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()

async def test_streaming():
    """Prueba del streaming en tiempo real."""
    print("\n🌊 Probando streaming...")
    print("-" * 40)
    
    agent = EconomIAssistAgent()
    message = "Explícame qué es la inflación y cómo afecta mis ahorros"
    
    print(f"📝 Pregunta: {message}")
    print("🤖 Respuesta streaming: ", end="", flush=True)
    
    try:
        async for chunk in agent.chat_stream(message):
            print(chunk, end="", flush=True)
        print("\n✅ Streaming exitoso")
    except Exception as e:
        print(f"\n❌ Error en streaming: {e}")

async def test_conversation_context():
    """Prueba que el contexto se mantenga entre mensajes."""
    print("\n💬 Probando contexto conversacional...")
    print("-" * 40)
    
    agent = EconomIAssistAgent()
    
    # Conversación con contexto
    messages = [
        "Tengo $50,000 pesos para invertir",
        "¿Cuáles son mis opciones?",  # Debería recordar los $50,000
        "¿Y si tengo un perfil conservador?"  # Debería recordar el contexto anterior
    ]
    
    from agents_mcp import RunnerContext
    context = RunnerContext()
    
    for i, message in enumerate(messages, 1):
        print(f"\n👤 Usuario: {message}")
        try:
            response = await agent.chat(message, context)
            print(f"🤖 Agente: {response[:150]}...")
        except Exception as e:
            print(f"❌ Error: {e}")

async def main():
    """Función principal de testing."""
    print("🚀 Iniciando tests del agente simplificado...")
    
    try:
        await test_basic_functionality()
        await test_streaming()
        await test_conversation_context()
        
        print("\n🎉 ¡Todos los tests completados!")
        print("\n💡 Para usar interactivamente, ejecuta:")
        print("   python src/agent/openai_agent_simple.py")
        
    except Exception as e:
        print(f"💥 Error general: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())