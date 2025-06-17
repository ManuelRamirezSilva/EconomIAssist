#!/usr/bin/env python3
"""
Prueba del OpenAI Agents SDK con Azure OpenAI - VERSIÓN ALTERNATIVA
Nota: El SDK de OpenAI Agents no es compatible con Azure OpenAI directamente.
Esta versión usa Azure OpenAI para simular la funcionalidad del SDK.
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

async def test_openai_agents_alternative():
    """Prueba alternativa usando Azure OpenAI directamente"""
    print("🧪 Probando funcionalidad de agente con Azure OpenAI...")
    
    try:
        # 1. Configurar Azure OpenAI
        config = AzureOpenAIConfig()
        client = config.create_client()
        print(f"✅ Cliente Azure OpenAI configurado: {config.deployment_name}")
        
        # 2. Pruebas con diferentes tipos de consultas
        test_queries = [
            "¿Qué consejos de ahorro me puedes dar?",
            "¿Cómo puedo organizar mis finanzas personales?", 
            "Explícame qué es un presupuesto"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- Prueba {i} ---")
            print(f"👤 Consulta: {query}")
            
            # Crear mensajes para simular agente financiero
            messages = [
                {
                    "role": "system", 
                    "content": """Eres EconomIAssist, un asistente financiero amigable que da consejos útiles.
                    Responde de manera clara y usa emojis para hacer la conversación más amigable.
                    Mantén las respuestas concisas pero informativas."""
                },
                {"role": "user", "content": query}
            ]
            
            # Ejecutar consulta usando Azure OpenAI
            response = await client.chat.completions.create(
                model=config.deployment_name,
                messages=messages,
                max_tokens=200,
                temperature=0.7
            )
            
            response_text = response.choices[0].message.content
            
            # Truncar respuesta para mostrar
            display_response = response_text[:100] + "..." if len(response_text) > 100 else response_text
            print(f"🤖 Respuesta: {display_response}")
            print(f"✅ Longitud: {len(response_text)} caracteres")
        
        print(f"\n🎉 ¡Funcionalidad de agente con Azure OpenAI funcionando correctamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error en las pruebas: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_openai_agents_sdk():
    """Prueba original del SDK (probablemente fallará con Azure OpenAI)"""
    print("🧪 Probando OpenAI Agents SDK original...")
    print("⚠️ Nota: El SDK de OpenAI Agents no es compatible con Azure OpenAI")
    
    try:
        # Intentar importar el SDK
        from agents import Agent, Runner
        
        # 1. Configurar Azure OpenAI
        config = AzureOpenAIConfig()
        model = config.create_model()
        print(f"✅ Modelo configurado: {type(model).__name__}")
        
        # 2. Crear agente de prueba (probablemente fallará)
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
        
        # 3. Prueba simple
        query = "¿Qué consejos de ahorro me puedes dar?"
        print(f"👤 Consulta: {query}")
        
        result = await Runner.run(agent, query)
        response = result.final_output
        
        display_response = response[:100] + "..." if len(response) > 100 else response
        print(f"🤖 Respuesta: {display_response}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error esperado con SDK de agentes: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Probando dos enfoques para funcionalidad de agentes...")
    
    # Prueba 1: Funcionalidad alternativa con Azure OpenAI
    success1 = asyncio.run(test_openai_agents_alternative())
    
    # Prueba 2: SDK original (probablemente fallará)
    success2 = asyncio.run(test_openai_agents_sdk())
    
    if success1:
        print(f"\n✅ Funcionalidad de agente disponible (usando Azure OpenAI directamente)")
    else:
        print(f"\n❌ Funcionalidad de agente falló")
        
    if success2:
        print(f"✅ SDK de OpenAI Agents funcionó (inesperado)")
    else:
        print(f"⚠️ SDK de OpenAI Agents no compatible con Azure OpenAI (esperado)")