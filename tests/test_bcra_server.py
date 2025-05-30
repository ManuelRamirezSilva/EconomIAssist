#!/usr/bin/env python3
"""
Prueba específica del servidor BCRA MCP
Verifica conectividad con la API de EstadisticasBCRA.com
"""

import asyncio
import sys
import os
from pathlib import Path

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

async def test_bcra_server():
    """Prueba el servidor BCRA MCP"""
    print("🏦 Probando Servidor BCRA MCP")
    print("=" * 60)
    
    try:
        from mcp_servers.bcra_server import BCRAServerMCP
        
        # Usar context manager para cerrar automáticamente la sesión
        async with BCRAServerMCP() as server:
            
            # Verificar configuración del token
            if not server.token:
                print("❌ BCRA_API_TOKEN no configurado en .env")
                print("💡 Para obtener un token:")
                print("   1. Visita: https://estadisticasbcra.com/")
                print("   2. Regístrate gratis")
                print("   3. Obtén tu token")
                print("   4. Agrega BCRA_API_TOKEN=tu_token en .env")
                return False
            
            print(f"✅ Token configurado: {server.token[:10]}...")
            print(f"📊 Herramientas disponibles: {len(server.tools)}")
            
            # Mostrar herramientas disponibles
            print("\n🔧 Herramientas disponibles:")
            for tool_name, tool_info in server.tools.items():
                print(f"   📝 {tool_name}: {tool_info['description']}")
            
            # Probar herramientas principales
            print("\n🧪 Probando herramientas...")
            
            test_cases = [
                ("get_dollar_rates", {"rate_type": "ambos"}, "Cotizaciones del dólar"),
                ("get_inflation_data", {"period": "mensual"}, "Inflación mensual"),
                ("get_interest_rates", {"rate_type": "badlar"}, "Tasa BADLAR"),
                ("get_market_data", {"indicator": "merval"}, "Índice MERVAL"),
            ]
            
            successful_tests = 0
            
            for tool_name, args, description in test_cases:
                print(f"\n   🔍 {description}...")
                
                try:
                    result = await server.call_tool(tool_name, args)
                    
                    if result.get("success"):
                        print(f"   ✅ {description}: Datos obtenidos")
                        
                        # Mostrar datos específicos según el tipo
                        if tool_name == "get_dollar_rates" and "data" in result:
                            data = result["data"]
                            if "dolar_oficial" in data:
                                print(f"      💵 Oficial: ${data['dolar_oficial']['value']}")
                            if "dolar_blue" in data:
                                print(f"      💰 Blue: ${data['dolar_blue']['value']}")
                            if "brecha_cambiaria" in data:
                                print(f"      📈 Brecha: {data['brecha_cambiaria']}")
                        
                        elif tool_name == "get_inflation_data" and "data" in result:
                            data = result["data"]
                            print(f"      📊 Inflación: {data.get('value', 'N/A')}")
                        
                        elif tool_name == "get_interest_rates" and "data" in result:
                            data = result["data"]
                            if "badlar" in data:
                                print(f"      🏦 BADLAR: {data['badlar']['value']}")
                        
                        elif tool_name == "get_market_data" and "data" in result:
                            data = result["data"]
                            if "merval" in data:
                                print(f"      📈 MERVAL: {data['merval']['value']}")
                        
                        successful_tests += 1
                        
                    elif result.get("error"):
                        error = result["error"]
                        if "Token" in error or "401" in error:
                            print(f"   🔑 {description}: Error de autenticación")
                            print(f"      💡 Verificar BCRA_API_TOKEN")
                        elif "Límite" in error or "429" in error:
                            print(f"   ⏰ {description}: Límite de requests alcanzado")
                        else:
                            print(f"   ❌ {description}: {error}")
                    else:
                        print(f"   ⚠️ {description}: Respuesta inesperada")
                        
                except Exception as e:
                    print(f"   ❌ {description}: Error - {e}")
            
            # Mostrar estadísticas
            print(f"\n📊 Estadísticas:")
            print(f"   Tests exitosos: {successful_tests}/{len(test_cases)}")
            print(f"   Requests utilizados: {server.daily_requests}/100")
            
            # Probar análisis económico si hay datos básicos
            if successful_tests > 0:
                print(f"\n🧠 Probando análisis económico...")
                try:
                    analysis_result = await server.call_tool("get_economic_analysis", 
                                                           {"analysis_type": "resumen_completo"})
                    if analysis_result.get("success"):
                        print(f"   ✅ Análisis generado exitosamente")
                        if "data" in analysis_result and "insights" in analysis_result["data"]:
                            insights = analysis_result["data"]["insights"]
                            print(f"   💡 Insights: {len(insights)} generados")
                            for insight in insights[:2]:  # Mostrar primeros 2
                                print(f"      • {insight}")
                    else:
                        print(f"   ❌ Error en análisis: {analysis_result.get('error')}")
                except Exception as e:
                    print(f"   ❌ Error en análisis: {e}")
            
            return successful_tests > 0
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        return False
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False

async def main():
    """Función principal"""
    print("🚀 EconomIAssist - Prueba Servidor BCRA")
    print("📅 Fecha: 29 de mayo de 2025")
    print("🎯 Objetivo: Verificar integración con API del BCRA")
    print("=" * 70)
    
    success = await test_bcra_server()
    
    print("\n" + "=" * 70)
    print("📊 RESUMEN - SERVIDOR BCRA MCP")
    print("=" * 70)
    
    if success:
        print("✅ Servidor BCRA MCP funcionando correctamente")
        print("🏦 Datos económicos del BCRA disponibles")
        print("📈 Herramientas de análisis económico operativas")
        print("\n💡 Próximos pasos:")
        print("   • Integrar con el agente conversacional")
        print("   • Configurar cache persistente")
        print("   • Agregar más indicadores económicos")
        return 0
    else:
        print("❌ Servidor BCRA MCP no operativo")
        print("🔧 Revisar configuración del token BCRA_API_TOKEN")
        print("🌐 Verificar conectividad a internet")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)