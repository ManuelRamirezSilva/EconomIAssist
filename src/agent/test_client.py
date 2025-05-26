#!/usr/bin/env python3
"""
Cliente simple para probar el servidor MCP EconomIAssist
"""

import asyncio
import sys
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Agregar utils al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.env_loader import load_environment_variables

# Cargar variables de entorno
load_environment_variables()

async def test_mcp_server():
    """Prueba todas las funcionalidades del servidor MCP"""
    
    # Configuración del servidor
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.join(os.path.dirname(__file__), "..", "mcp_server", "server.py")],
        env=None
    )
    
    print("🔌 Conectando al servidor MCP...")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Inicializar la conexión
                await session.initialize()
                print("✅ Conexión establecida con el servidor MCP")
                
                # Probar herramienta echo
                print("\n📡 Probando herramienta 'echo'...")
                result = await session.call_tool("echo", {"message": "¡Hola desde el cliente MCP!"})
                print(f"Resultado: {result.content[0].text}")
                
                # Registrar algunas transacciones de prueba
                print("\n💰 Registrando transacciones de prueba...")
                
                transacciones_prueba = [
                    {"tipo": "ingreso", "monto": 500.0, "descripcion": "Salario", "categoria": "trabajo"},
                    {"tipo": "gasto", "monto": 50.0, "descripcion": "Almuerzo", "categoria": "comida"},
                    {"tipo": "gasto", "monto": 25.0, "descripcion": "Transporte", "categoria": "transporte"}
                ]
                
                for transaccion in transacciones_prueba:
                    result = await session.call_tool("registrar_transaccion", transaccion)
                    print(f"✅ {result.content[0].text}")
                
                # Obtener saldo actual
                print("\n💳 Consultando saldo actual...")
                result = await session.call_tool("obtener_saldo", {})
                print(f"Saldo: {result.content[0].text}")
                
                # Obtener todas las transacciones
                print("\n📋 Obteniendo lista de transacciones...")
                result = await session.call_tool("obtener_transacciones", {})
                print(f"Transacciones: {result.content[0].text}")
                
                # Leer el recurso de resumen
                print("\n📊 Leyendo resumen financiero...")
                content, mime_type = await session.read_resource("economiassist://resumen")
                print(f"Resumen:\n{content}")
                
                print("\n🎉 ¡Todas las pruebas completadas exitosamente!")
                
    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()

def run_interactive_test():
    """Ejecuta pruebas interactivas con el usuario"""
    print("🧪 EconomIAssist - Cliente de Pruebas MCP")
    print("="*50)
    
    try:
        asyncio.run(test_mcp_server())
    except KeyboardInterrupt:
        print("\n👋 Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        # Modo interactivo para pruebas manuales
        run_interactive_test()
    else:
        # Modo automático para pruebas rápidas
        asyncio.run(test_mcp_server())