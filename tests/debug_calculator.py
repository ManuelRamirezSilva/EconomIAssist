#!/usr/bin/env python3
"""
Debug específico para el servidor MCP de calculadora
"""

import asyncio
import json
import subprocess

async def test_calculator_detailed():
    """Prueba detallada del servidor de calculadora"""
    print("🔧 Debugging servidor MCP de calculadora...")
    
    try:
        # Iniciar proceso del servidor
        process = await asyncio.create_subprocess_exec(
            "python", "-m", "mcp_server_calculator",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        print("✅ Proceso iniciado correctamente")
        
        # Enviar mensaje de inicialización
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {}
                },
                "clientInfo": {
                    "name": "EconomIAssist",
                    "version": "1.0.0"
                }
            }
        }
        
        message = json.dumps(init_request) + "\n"
        process.stdin.write(message.encode())
        await process.stdin.drain()
        print("📤 Mensaje de inicialización enviado")
        
        # Leer respuesta con timeout
        try:
            line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
            if line:
                response = json.loads(line.decode().strip())
                print(f"📥 Respuesta de inicialización: {response}")
                
                if "result" in response:
                    print("✅ Inicialización exitosa")
                    
                    # Enviar mensaje initialized
                    initialized_notification = {
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized"
                    }
                    
                    message = json.dumps(initialized_notification) + "\n"
                    process.stdin.write(message.encode())
                    await process.stdin.drain()
                    print("📤 Mensaje 'initialized' enviado")
                    
                    # Esperar un poco
                    await asyncio.sleep(0.1)
                    
                    # Solicitar lista de herramientas
                    tools_request = {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/list"
                    }
                    
                    message = json.dumps(tools_request) + "\n"
                    process.stdin.write(message.encode())
                    await process.stdin.drain()
                    print("📤 Solicitud de herramientas enviada")
                    
                    # Leer respuesta de herramientas
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
                    if line:
                        tools_response = json.loads(line.decode().strip())
                        print(f"📥 Respuesta de herramientas: {tools_response}")
                        
                        if "result" in tools_response:
                            tools = tools_response["result"].get("tools", [])
                            print(f"🔧 Herramientas encontradas: {len(tools)}")
                            for tool in tools:
                                print(f"   - {tool.get('name', 'Sin nombre')}: {tool.get('description', 'Sin descripción')}")
                        
                        return True
                    else:
                        print("❌ No se recibió respuesta de herramientas")
                        return False
                else:
                    print(f"❌ Error en inicialización: {response}")
                    return False
            else:
                print("❌ No se recibió respuesta de inicialización")
                return False
                
        except asyncio.TimeoutError:
            print("❌ Timeout esperando respuesta")
            return False
        
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
        return False
    
    finally:
        if 'process' in locals():
            process.terminate()
            await process.wait()

if __name__ == "__main__":
    success = asyncio.run(test_calculator_detailed())
    print(f"\n{'✅ EXITOSO' if success else '❌ FALLÓ'}")