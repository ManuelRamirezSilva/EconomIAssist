#!/usr/bin/env python3
"""
Prueba MCP Puro - KnowledgeBase Server
Verifica que el servidor se conecte y auto-descubra herramientas sin código específico
"""

import asyncio
import sys
import os
from pathlib import Path

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

async def test_mcp_pure_approach():
    """Prueba el enfoque MCP puro sin métodos específicos"""
    print("🧪 Probando Enfoque MCP Puro - KnowledgeBase Server")
    print("=" * 60)
    
    try:
        from agent.mcp_client import MCPManager
        
        # Inicializar MCPManager (sin métodos específicos)
        manager = MCPManager()
        
        # Auto-conectar servidores según configuración YAML
        print("🔌 Auto-conectando servidores MCP...")
        results = await manager.auto_connect_servers()
        
        print(f"📊 Resultados de conexión:")
        for server_name, success in results.items():
            status = "✅" if success else "❌"
            print(f"   {server_name}: {status}")
        
        # Verificar que KnowledgeBase se conectó
        if "knowledge_base" not in results or not results["knowledge_base"]:
            print("\n❌ KnowledgeBase Server no conectado")
            print("💡 Verifique que Docker esté ejecutándose")
            return False
        
        print("\n✅ KnowledgeBase Server conectado exitosamente!")
        
        # Mostrar herramientas auto-descubiertas
        print("\n🔍 Herramientas auto-descubiertas:")
        tools_by_server = await manager.get_available_tools()
        
        for server_name, tools in tools_by_server.items():
            print(f"   📦 {server_name}:")
            for tool in tools:
                print(f"      🔧 {tool}")
        
        # Mostrar estadísticas MCP
        stats = manager.get_connection_stats()
        print(f"\n📈 Estadísticas MCP:")
        print(f"   Servidores conectados: {stats['connected_servers']}")
        print(f"   Total herramientas: {stats['total_tools']}")
        print(f"   Capacidades: {list(stats['servers_by_capability'].keys())}")
        
        # Verificar capacidades de memoria
        if "user_memory" in stats['servers_by_capability']:
            print(f"\n🧠 Capacidad de memoria detectada!")
            memory_servers = stats['servers_by_capability']['user_memory']
            print(f"   Servidores con memoria: {memory_servers}")
        else:
            print(f"\n⚠️ Capacidad de memoria no detectada")
        
        # Limpiar conexiones
        await manager.disconnect_all()
        print(f"\n🔌 Desconectado de todos los servidores")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        return False
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
        return False

async def test_agent_with_pure_mcp():
    """Prueba el agente usando el enfoque MCP puro"""
    print("\n🤖 Probando Agente con MCP Puro")
    print("=" * 60)
    
    try:
        from agent.conversational_agent import ConversationalAgent
        
        # Inicializar agente (sin modificaciones específicas)
        agent = ConversationalAgent()
        initialized = await agent.initialize()
        
        if not initialized:
            print("❌ No se pudo inicializar el agente")
            return False
        
        print("✅ Agente inicializado con MCP puro")
        
        # Verificar que las herramientas MCP se auto-descubrieron
        if hasattr(agent, 'mcp_functions') and agent.mcp_functions:
            print(f"\n🔧 Funciones MCP auto-descubiertas: {len(agent.mcp_functions)}")
            for func in agent.mcp_functions[:3]:  # Mostrar primeras 3
                print(f"   📝 {func.get('name', 'sin_nombre')}: {func.get('description', '')[:50]}...")
        else:
            print("\n⚠️ No se auto-descubrieron funciones MCP")
        
        # Simular una consulta que podría usar memoria
        test_query = "¿Recordás alguna conversación anterior que hayamos tenido?"
        print(f"\n💬 Consulta de prueba: {test_query}")
        
        try:
            response = await agent.process_user_input(test_query)
            print(f"✅ Respuesta generada ({len(response)} caracteres)")
            print(f"📄 Preview: {response[:150]}...")
        except Exception as e:
            print(f"❌ Error procesando consulta: {e}")
        
        # Limpiar recursos
        await agent.cleanup()
        print("\n🧹 Recursos del agente limpiados")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        return False
    except Exception as e:
        print(f"❌ Error en prueba del agente: {e}")
        return False

async def main():
    """Función principal"""
    print("🚀 EconomIAssist - Prueba MCP Puro")
    print("📅 Fecha: 28 de mayo de 2025")
    print("🎯 Objetivo: Verificar enfoque MCP sin código específico")
    print("=" * 70)
    
    # Verificar Docker
    print("🐳 Verificando Docker...")
    import subprocess
    try:
        result = subprocess.run(["docker", "--version"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Docker disponible")
        else:
            print("❌ Docker no funcional")
            return 1
    except Exception:
        print("❌ Docker no instalado")
        return 1
    
    results = {}
    
    # Prueba 1: MCP Manager puro
    results['mcp_pure'] = await test_mcp_pure_approach()
    
    # Prueba 2: Agente completo (solo si MCP funciona)
    if results['mcp_pure']:
        results['agent_pure'] = await test_agent_with_pure_mcp()
    else:
        results['agent_pure'] = False
        print("\n⚠️ Saltando prueba del agente - MCP no funcional")
    
    # Resumen
    print("\n" + "=" * 70)
    print("📊 RESUMEN - ENFOQUE MCP PURO")
    print("=" * 70)
    
    for test_name, success in results.items():
        status = "✅ EXITOSO" if success else "❌ FALLÓ"
        test_display = {
            'mcp_pure': 'MCP Manager (Auto-descubrimiento)',
            'agent_pure': 'Agente Conversacional (MCP Puro)'
        }
        print(f"   {test_display[test_name]:<30} {status}")
    
    total_passed = sum(1 for success in results.values() if success)
    total_tests = len(results)
    
    print(f"\n🎯 Resultado: {total_passed}/{total_tests} pruebas exitosas")
    
    if total_passed == total_tests:
        print("🎉 ¡Enfoque MCP Puro funcionando perfectamente!")
        print("🧠 KnowledgeBase Server integrado sin código específico")
        print("🔧 Herramientas auto-descubiertas dinámicamente")
        return 0
    else:
        print("⚠️ Revisar configuración de Docker o conectividad")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)