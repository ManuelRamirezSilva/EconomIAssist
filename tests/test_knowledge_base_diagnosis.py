#!/usr/bin/env python3
"""
Prueba específica para diagnosticar la comunicación con knowledge_base server
"""

import asyncio
import json
import sys
import os

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

async def test_knowledge_base_direct():
    """Prueba comunicación directa con el knowledge_base server"""
    print("🧪 Probando comunicación directa con knowledge_base server...")
    
    try:
        # Método 1: Usar docker exec con stdin directo
        print("\n📝 Método 1: docker exec con stdin directo")
        process = await asyncio.create_subprocess_exec(
            "docker", "exec", "-i", "economyassist-kb", "sh",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Enviar mensaje de inicialización MCP
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "resources": {}},
                "clientInfo": {"name": "EconomIAssist", "version": "1.0.0"}
            }
        }
        
        message_str = json.dumps(init_message) + "\n"
        print(f"   Enviando: {message_str.strip()}")
        
        process.stdin.write(message_str.encode())
        await process.stdin.drain()
        
        # Intentar leer respuesta
        try:
            line = await asyncio.wait_for(process.stdout.readline(), timeout=5)
            if line:
                response = line.decode().strip()
                print(f"   Respuesta: {response}")
                
                try:
                    parsed = json.loads(response)
                    print(f"   ✅ JSON válido: {parsed}")
                except json.JSONDecodeError:
                    print(f"   ❌ No es JSON válido")
            else:
                print("   ❌ No hay respuesta")
        except asyncio.TimeoutError:
            print("   ❌ Timeout esperando respuesta")
        
        process.terminate()
        await process.wait()
        
    except Exception as e:
        print(f"❌ Error en método 1: {e}")
    
    try:
        # Método 2: Comunicación directa con el proceso principal del contenedor
        print("\n📝 Método 2: Comunicación directa con proceso principal")
        
        # Intentar conectar directamente al proceso principal del contenedor
        process = await asyncio.create_subprocess_exec(
            "docker", "exec", "-i", "economyassist-kb", "cat",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Enviar mensaje MCP
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "resources": {}},
                "clientInfo": {"name": "EconomIAssist", "version": "1.0.0"}
            }
        }
        
        message_str = json.dumps(init_message) + "\n"
        print(f"   Enviando: {message_str.strip()}")
        
        process.stdin.write(message_str.encode())
        await process.stdin.drain()
        
        # Intentar leer respuesta
        try:
            line = await asyncio.wait_for(process.stdout.readline(), timeout=5)
            if line:
                response = line.decode().strip()
                print(f"   Respuesta: {response}")
                
                try:
                    parsed = json.loads(response)
                    print(f"   ✅ JSON válido: {parsed}")
                except json.JSONDecodeError:
                    print(f"   ❌ No es JSON válido")
            else:
                print("   ❌ No hay respuesta")
        except asyncio.TimeoutError:
            print("   ❌ Timeout esperando respuesta")
        
        process.terminate()
        await process.wait()
        
    except Exception as e:
        print(f"❌ Error en método 2: {e}")

async def test_knowledge_base_container_inspection():
    """Inspecciona el contenedor para entender mejor su configuración"""
    print("\n🔍 Inspeccionando contenedor knowledge_base...")
    
    try:
        # Obtener información del contenedor
        process = await asyncio.create_subprocess_exec(
            "docker", "inspect", "economyassist-kb",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            import json
            container_info = json.loads(stdout.decode())[0]
            
            print(f"   📦 Imagen: {container_info.get('Config', {}).get('Image', 'N/A')}")
            print(f"   🚀 Comando: {container_info.get('Config', {}).get('Cmd', 'N/A')}")
            print(f"   📍 Punto de entrada: {container_info.get('Config', {}).get('Entrypoint', 'N/A')}")
            print(f"   🌐 Puertos: {container_info.get('Config', {}).get('ExposedPorts', {})}")
            print(f"   📂 Directorio de trabajo: {container_info.get('Config', {}).get('WorkingDir', 'N/A')}")
            
            # Ver procesos ejecutándose en el contenedor
            print("\n   🔄 Procesos en ejecución:")
            proc_process = await asyncio.create_subprocess_exec(
                "docker", "exec", "economyassist-kb", "ps", "aux",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            proc_stdout, _ = await proc_process.communicate()
            print(proc_stdout.decode())
            
        else:
            print(f"   ❌ Error inspeccionando contenedor: {stderr.decode()}")
            
    except Exception as e:
        print(f"❌ Error inspeccionando contenedor: {e}")

async def main():
    """Función principal de diagnóstico"""
    print("🔧 EconomIAssist - Diagnóstico Knowledge Base Server")
    print("=" * 60)
    
    await test_knowledge_base_container_inspection()
    await test_knowledge_base_direct()
    
    print("\n💡 Diagnóstico completado")

if __name__ == "__main__":
    asyncio.run(main())