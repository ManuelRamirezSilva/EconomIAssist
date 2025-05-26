#!/usr/bin/env python3
"""
Prueba rápida de conectividad con Azure OpenAI
"""

import asyncio
import sys
import os

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent.conversational_agent import AzureOpenAIConfig

async def test_azure_connection():
    """Prueba rápida de conectividad con Azure OpenAI"""
    print("🔍 Verificando conectividad con Azure OpenAI...")
    
    try:
        # 1. Cargar configuración
        config = AzureOpenAIConfig()
        print(f"✅ Configuración cargada:")
        print(f"   📍 Endpoint: {config.api_base}")
        print(f"   🤖 Deployment: {config.deployment_name}")
        print(f"   🔑 API Version: {config.api_version}")
        
        # 2. Crear cliente
        client = config.create_client()
        print(f"✅ Cliente Azure OpenAI creado")
        
        # 3. Crear modelo
        model = config.create_model()
        print(f"✅ Modelo configurado: {type(model).__name__}")
        
        # 4. Probar una llamada simple (usando DEPLOYMENT name, no model name)
        print(f"🚀 Probando llamada directa a Azure OpenAI...")
        print(f"   Usando deployment: {config.deployment_name}")
        
        response = await client.chat.completions.create(
            model=config.deployment_name,  # Usar deployment name, no modelo base
            messages=[
                {"role": "user", "content": "¿Puedes responder con 'Conexión exitosa'?"}
            ],
            max_tokens=50,
            temperature=0.1
        )
        
        response_text = response.choices[0].message.content
        print(f"✅ Respuesta de Azure OpenAI: {response_text}")
        
        print(f"\n🎉 ¡Conectividad con Azure OpenAI verificada exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error de conectividad: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_azure_connection())
    if success:
        print(f"\n✅ Prueba completada exitosamente")
    else:
        print(f"\n❌ Prueba falló")
        exit(1)