#!/usr/bin/env python3
"""
Test de Integración Final - Agente Conversacional EconomIAssist
Verifica las 3 capacidades principales: Búsqueda Web, Memoria Personal y Cálculos
"""

import asyncio
import sys
import os
from pathlib import Path

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

async def test_final_integration():
    """Prueba la integración final del agente conversacional"""
    print("🎯 EconomIAssist - Test de Integración Final")
    print("=" * 70)
    print("🎯 Objetivo: Verificar agente conversacional completo")
    print("🔍 Búsqueda Web: Tavily API")
    print("💾 Memoria Personal: Knowledge Base")
    print("🧮 Cálculos: Calculator MCP")
    print("🤖 Agente: Azure OpenAI GPT-4o-mini")
    print("=" * 70)
    
    try:
        from agent.conversational_agent import ConversationalAgent
        
        # Inicializar agente
        print("\n🚀 Inicializando agente conversacional...")
        agent = ConversationalAgent()
        initialized = await agent.initialize()
        
        if not initialized:
            print("❌ No se pudo inicializar el agente")
            return False
        
        print("✅ Agente inicializado correctamente")
        
        # Verificar conexiones esperadas
        expected_servers = ['tavily', 'knowledge_base', 'calculator']
        connected_servers = []
        
        for server_name in expected_servers:
            if server_name in agent.mcp_manager.connections:
                connection = agent.mcp_manager.connections[server_name]
                if connection.is_connected:
                    connected_servers.append(server_name)
                    print(f"✅ {server_name}: Conectado ({len(connection.tools)} herramientas)")
                else:
                    print(f"❌ {server_name}: No conectado")
            else:
                print(f"❌ {server_name}: No encontrado")
        
        if len(connected_servers) < 2:  # Al menos 2 de 3 servidores
            print(f"⚠️ Solo {len(connected_servers)}/3 servidores conectados")
            print("El agente funcionará con capacidades limitadas")
        
        # Mostrar estadísticas de conexiones
        print(f"\n📊 Estadísticas de conexiones MCP:")
        stats = agent.mcp_manager.get_connection_stats()
        print(f"   🔗 Servidores conectados: {stats['connected_servers']}/{stats['total_servers']}")
        print(f"   🔧 Total herramientas: {stats['total_tools']}")
        print(f"   📋 Capacidades: {', '.join(stats['servers_by_capability'].keys())}")
        
        # Pruebas de conversación con diferentes capacidades
        print(f"\n💬 Probando capacidades del agente...")
        
        test_scenarios = [
            {
                "name": "Búsqueda de información económica",
                "query": "¿Cuál está la cotización del dólar en Argentina hoy?",
                "capability": "web_search"
            },
            {
                "name": "Cálculo financiero",
                "query": "Si tengo $100,000 pesos y quiero ahorrar el 20%, ¿cuánto debería ahorrar?",
                "capability": "mathematical_calculations"
            },
            {
                "name": "Memoria personal",
                "query": "Guarda que mi sueldo mensual es de $500,000 pesos argentinos",
                "capability": "user_memory"
            },
            {
                "name": "Recuperación de memoria",
                "query": "¿Cuánto es mi sueldo mensual?",
                "capability": "user_memory"
            }
        ]
        
        results = []
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n🔍 Test {i}: {scenario['name']}")
            print(f"   Consulta: {scenario['query']}")
            
            try:
                response = await agent.process_query(scenario['query'])
                print(f"✅ Respuesta generada ({len(response)} caracteres)")
                print(f"📄 Preview: {response[:200]}...")
                
                # Verificar que la respuesta es útil
                if len(response) > 50 and "error" not in response.lower():
                    print(f"   💡 Respuesta útil: ✅")
                    results.append(True)
                else:
                    print(f"   💡 Respuesta útil: ⚠️")
                    results.append(False)
                    
            except Exception as e:
                print(f"❌ Error en consulta: {e}")
                results.append(False)
        
        # Calcular tasa de éxito
        success_rate = sum(results) / len(results) * 100
        print(f"\n📊 Tasa de éxito: {success_rate:.1f}% ({sum(results)}/{len(results)} tests)")
        
        await agent.cleanup()
        return success_rate >= 50  # Al menos 50% de éxito
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        return False
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False

async def main():
    """Función principal"""
    success = await test_final_integration()
    
    print("\n" + "=" * 70)
    print("📊 RESUMEN FINAL - ECONOMASSIST")
    print("=" * 70)
    
    if success:
        print("✅ INTEGRACIÓN FINAL EXITOSA")
        print("🎉 EconomIAssist está listo para usar!")
        print("\n🚀 Características principales:")
        print("   🔍 Búsqueda web de información financiera")
        print("   💾 Memoria personal y contextual")
        print("   🧮 Cálculos matemáticos precisos")
        print("   🤖 Conversación natural con Azure OpenAI")
        print("   📊 Análisis financiero personalizado")
        print("\n💡 Ejemplos de uso:")
        print("   • '¿Cuál es el dólar blue hoy?'")
        print("   • 'Gasté $50,000 en supermercado'")
        print("   • 'Calcula el 15% de mi sueldo'")
        print("   • '¿Cuánto gasté este mes?'")
        print("   • 'Dame consejos para ahorrar'")
        print("\n🎯 Para usar el agente:")
        print("   python src/agent/conversational_agent.py")
        return 0
    else:
        print("❌ INTEGRACIÓN FINAL CON PROBLEMAS")
        print("⚠️ El agente puede funcionar con capacidades limitadas")
        print("🔧 Revisar configuración de servidores MCP")
        print("🔑 Verificar variables de entorno (.env)")
        print("🌐 Verificar conectividad de servicios")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)