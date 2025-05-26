#!/usr/bin/env python3
"""
Prueba del OpenAI Agents SDK con Azure OpenAI
"""

import asyncio
import sys
import os
import warnings

# Suprimir warnings de tracing
warnings.filterwarnings("ignore")
os.environ["OPENAI_LOG_LEVEL"] = "ERROR"

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent.conversational_agent import AzureOpenAIConfig
from agents import Agent, Runner

async def test_openai_agents_sdk():
    """Prueba el OpenAI Agents SDK con diferentes tipos de consultas"""
    print("🧪 Probando OpenAI Agents SDK con Azure OpenAI...")
    
    try:
        # 1. Configurar Azure OpenAI
        config = AzureOpenAIConfig()
        model = config.create_model()
        print(f"✅ Modelo Azure OpenAI configurado: {config.deployment_name}")
        
        # 2. Crear agente de prueba
        agent = Agent(
            name="TestAgent",
            model=model,
            instructions="""
            Eres un asistente financiero amigable que da consejos útiles.
            Responde de manera clara y usa emojis para hacer la conversación más amigable.
            Mantén las respuestas concisas pero informativas.
            """
        )
        print(f"✅ Agente creado: {agent.name}")
        
        # 3. Pruebas con diferentes tipos de consultas
        test_queries = [
            "¿Qué consejos de ahorro me puedes dar?",
            "¿Cómo puedo organizar mis finanzas personales?", 
            "Explícame qué es un presupuesto"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- Prueba {i} ---")
            print(f"👤 Consulta: {query}")
            
            # Suprimir output de tracing durante la ejecución
            import logging
            logging.getLogger("openai").setLevel(logging.ERROR)
            
            # Ejecutar consulta
            result = await Runner.run(agent, query)
            response = result.final_output
            
            # Truncar respuesta para mostrar
            display_response = response[:100] + "..." if len(response) > 100 else response
            print(f"🤖 Respuesta: {display_response}")
            print(f"✅ Longitud: {len(response)} caracteres")
        
        print(f"\n🎉 ¡OpenAI Agents SDK funcionando correctamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error en las pruebas: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_openai_agents_sdk())
    if success:
        print(f"\n✅ Prueba del SDK completada exitosamente")
    else:
        print(f"\n❌ Prueba del SDK falló")
        exit(1)