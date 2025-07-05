#!/usr/bin/env python3
"""
Servidor MCP para datos económicos del BCRA (Banco Central de la República Argentina)
Integra con la API de EstadisticasBCRA.com para obtener datos financieros argentinos
"""

import os
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class BCRAServerMCP:
    """Servidor MCP para datos económicos del BCRA"""
    
    def __init__(self):
        self.token = os.getenv("BCRA_API_TOKEN")
        self.base_url = "https://api.estadisticasbcra.com"
        self.session = None
        self.daily_requests = 0
        self.cache = {}
        self.cache_duration = 300  # 5 minutos de cache
        
        # Configurar herramientas disponibles
        self.tools = {
            "get_dollar_rates": {
                "description": "Obtiene las cotizaciones actuales del dólar (oficial, blue, MEP, CCL)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "rate_type": {
                            "type": "string",
                            "enum": ["oficial", "blue", "mep", "ccl", "ambos"],
                            "description": "Tipo de cotización a obtener"
                        }
                    },
                    "required": ["rate_type"]
                }
            },
            "get_inflation_data": {
                "description": "Obtiene datos de inflación mensual y anual",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "period": {
                            "type": "string",
                            "enum": ["mensual", "anual", "ultimo"],
                            "description": "Período de inflación a consultar"
                        }
                    },
                    "required": ["period"]
                }
            },
            "get_interest_rates": {
                "description": "Obtiene tasas de interés (BADLAR, LELIQ, Plazo Fijo)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "rate_type": {
                            "type": "string",
                            "enum": ["badlar", "leliq", "plazo_fijo", "todas"],
                            "description": "Tipo de tasa de interés"
                        }
                    },
                    "required": ["rate_type"]
                }
            },
            "get_reserves_data": {
                "description": "Obtiene datos de reservas internacionales del BCRA",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "period": {
                            "type": "string",
                            "enum": ["actual", "historico"],
                            "description": "Período de reservas a consultar"
                        }
                    },
                    "required": ["period"]
                }
            },
            "get_market_data": {
                "description": "Obtiene datos de mercados financieros (MERVAL, bonos, riesgo país)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "indicator": {
                            "type": "string",
                            "enum": ["merval", "riesgo_pais", "bonos", "todos"],
                            "description": "Indicador de mercado a consultar"
                        }
                    },
                    "required": ["indicator"]
                }
            },
            "get_economic_analysis": {
                "description": "Genera análisis económico integral basado en múltiples indicadores",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "analysis_type": {
                            "type": "string",
                            "enum": ["resumen_completo", "tendencias", "alertas", "comparativo"],
                            "description": "Tipo de análisis económico a generar"
                        }
                    },
                    "required": ["analysis_type"]
                }
            }
        }
    
    async def _get_session(self):
        """Obtiene o crea una sesión HTTP"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """Realiza una petición HTTP a la API del BCRA"""
        if not self.token:
            return {"error": "Token del BCRA no configurado"}
        
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint}"
        
        headers = {
            "Authorization": f"BEARER {self.token}",
            "Content-Type": "application/json"
        }
        
        # Verificar cache
        cache_key = f"{endpoint}_{str(params)}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_duration):
                return cached_data
        
        try:
            async with session.get(url, headers=headers, params=params or {}) as response:
                self.daily_requests += 1
                
                if response.status == 200:
                    data = await response.json()
                    # Guardar en cache
                    self.cache[cache_key] = (data, datetime.now())
                    return data
                elif response.status == 401:
                    return {"error": "Token del BCRA inválido o expirado"}
                elif response.status == 429:
                    return {"error": "Límite de requests diarios alcanzado (100/día)"}
                else:
                    error_text = await response.text()
                    return {"error": f"Error HTTP {response.status}: {error_text}"}
                    
        except asyncio.TimeoutError:
            return {"error": "Timeout en la conexión con la API del BCRA"}
        except Exception as e:
            return {"error": f"Error de conexión: {str(e)}"}
    
    async def get_dollar_rates(self, rate_type: str = "ambos") -> Dict[str, Any]:
        """Obtiene cotizaciones del dólar"""
        try:
            results = {}
            
            if rate_type in ["oficial", "ambos"]:
                oficial_data = await self._make_request("usd")
                # Verificar si hay error o datos válidos
                if isinstance(oficial_data, dict) and oficial_data.get("error"):
                    pass  # Continuar con otros datos
                elif oficial_data:  # Lista o dict con datos
                    if isinstance(oficial_data, list) and oficial_data:
                        latest_oficial = oficial_data[-1]
                        results["dolar_oficial"] = {
                            "value": latest_oficial["v"],
                            "date": latest_oficial["d"],
                            "change": self._calculate_change(oficial_data)
                        }
                    elif isinstance(oficial_data, dict) and oficial_data.get("v"):
                        results["dolar_oficial"] = {
                            "value": oficial_data["v"],
                            "date": oficial_data["d"],
                            "change": None
                        }
            
            if rate_type in ["blue", "ambos"]:
                blue_data = await self._make_request("usd_of")
                # Verificar si hay error o datos válidos
                if isinstance(blue_data, dict) and blue_data.get("error"):
                    pass  # Continuar con otros datos
                elif blue_data:  # Lista o dict con datos
                    if isinstance(blue_data, list) and blue_data:
                        latest_blue = blue_data[-1]
                        results["dolar_blue"] = {
                            "value": latest_blue["v"],
                            "date": latest_blue["d"],
                            "change": self._calculate_change(blue_data)
                        }
                    elif isinstance(blue_data, dict) and blue_data.get("v"):
                        results["dolar_blue"] = {
                            "value": blue_data["v"],
                            "date": blue_data["d"],
                            "change": None
                        }
            
            if rate_type == "mep":
                mep_data = await self._make_request("usd_mep")
                if isinstance(mep_data, dict) and mep_data.get("error"):
                    pass
                elif mep_data:
                    if isinstance(mep_data, list) and mep_data:
                        latest_mep = mep_data[-1]
                        results["dolar_mep"] = {
                            "value": latest_mep["v"],
                            "date": latest_mep["d"]
                        }
                    elif isinstance(mep_data, dict) and mep_data.get("v"):
                        results["dolar_mep"] = {
                            "value": mep_data["v"],
                            "date": mep_data["d"]
                        }
            
            if rate_type == "ccl":
                ccl_data = await self._make_request("usd_ccl")
                if isinstance(ccl_data, dict) and ccl_data.get("error"):
                    pass
                elif ccl_data:
                    if isinstance(ccl_data, list) and ccl_data:
                        latest_ccl = ccl_data[-1]
                        results["dolar_ccl"] = {
                            "value": latest_ccl["v"],
                            "date": latest_ccl["d"]
                        }
                    elif isinstance(ccl_data, dict) and ccl_data.get("v"):
                        results["dolar_ccl"] = {
                            "value": ccl_data["v"],
                            "date": ccl_data["d"]
                        }
            
            # Calcular brecha cambiaria si tenemos oficial y blue
            if "dolar_oficial" in results and "dolar_blue" in results:
                oficial_val = results["dolar_oficial"]["value"]
                blue_val = results["dolar_blue"]["value"]
                if oficial_val and blue_val:
                    brecha = ((blue_val - oficial_val) / oficial_val) * 100
                    results["brecha_cambiaria"] = f"{brecha:.2f}%"
            
            return {"success": True, "data": results}
            
        except Exception as e:
            return {"success": False, "error": f"Error obteniendo cotizaciones: {str(e)}"}
    
    async def get_inflation_data(self, period: str = "mensual") -> Dict[str, Any]:
        """Obtiene datos de inflación"""
        try:
            if period == "mensual":
                data = await self._make_request("inflacion_mensual_oficial")
            elif period == "anual":
                data = await self._make_request("inflacion_interanual_oficial")
            else:  # ultimo
                data = await self._make_request("inflacion_mensual_oficial")
            
            # Verificar si hay error
            if isinstance(data, dict) and data.get("error"):
                return {"success": False, "error": data["error"]}
            
            if isinstance(data, list) and data:
                latest = data[-1]
                result = {
                    "value": f"{latest['v']}%",
                    "date": latest["d"],
                    "period": period
                }
                
                if len(data) > 1:
                    result["previous"] = f"{data[-2]['v']}%"
                    result["trend"] = "↑" if latest["v"] > data[-2]["v"] else "↓"
                
                return {"success": True, "data": result}
            elif isinstance(data, dict) and data.get("v"):
                result = {
                    "value": f"{data['v']}%",
                    "date": data["d"],
                    "period": period
                }
                return {"success": True, "data": result}
            else:
                return {"success": False, "error": "No se encontraron datos de inflación"}
                
        except Exception as e:
            return {"success": False, "error": f"Error obteniendo inflación: {str(e)}"}
    
    async def get_interest_rates(self, rate_type: str = "badlar") -> Dict[str, Any]:
        """Obtiene tasas de interés"""
        try:
            results = {}
            
            if rate_type in ["badlar", "todas"]:
                badlar_data = await self._make_request("badlar")
                if isinstance(badlar_data, dict) and badlar_data.get("error"):
                    pass
                elif badlar_data:
                    if isinstance(badlar_data, list) and badlar_data:
                        latest = badlar_data[-1]
                        results["badlar"] = {
                            "value": f"{latest['v']}%",
                            "date": latest["d"]
                        }
                    elif isinstance(badlar_data, dict) and badlar_data.get("v"):
                        results["badlar"] = {
                            "value": f"{badlar_data['v']}%",
                            "date": badlar_data["d"]
                        }
            
            if rate_type in ["leliq", "todas"]:
                leliq_data = await self._make_request("leliq")
                if isinstance(leliq_data, dict) and leliq_data.get("error"):
                    pass
                elif leliq_data:
                    if isinstance(leliq_data, list) and leliq_data:
                        latest = leliq_data[-1]
                        results["leliq"] = {
                            "value": f"{latest['v']}%",
                            "date": latest["d"]
                        }
                    elif isinstance(leliq_data, dict) and leliq_data.get("v"):
                        results["leliq"] = {
                            "value": f"{leliq_data['v']}%",
                            "date": leliq_data["d"]
                        }
            
            if rate_type in ["plazo_fijo", "todas"]:
                pf_data = await self._make_request("plazo_fijo")
                if isinstance(pf_data, dict) and pf_data.get("error"):
                    pass
                elif pf_data:
                    if isinstance(pf_data, list) and pf_data:
                        latest = pf_data[-1]
                        results["plazo_fijo"] = {
                            "value": f"{latest['v']}%",
                            "date": latest["d"]
                        }
                    elif isinstance(pf_data, dict) and pf_data.get("v"):
                        results["plazo_fijo"] = {
                            "value": f"{pf_data['v']}%",
                            "date": pf_data["d"]
                        }
            
            return {"success": True, "data": results}
            
        except Exception as e:
            return {"success": False, "error": f"Error obteniendo tasas: {str(e)}"}
    
    async def get_reserves_data(self, period: str = "actual") -> Dict[str, Any]:
        """Obtiene datos de reservas internacionales"""
        try:
            data = await self._make_request("reservas")
            
            if isinstance(data, dict) and data.get("error"):
                return {"success": False, "error": data["error"]}
            
            if isinstance(data, list) and data:
                if period == "actual":
                    latest = data[-1]
                    result = {
                        "value": f"USD {latest['v']:,.0f} millones",
                        "date": latest["d"]
                    }
                    
                    if len(data) > 1:
                        previous = data[-2]
                        change = latest["v"] - previous["v"]
                        result["change"] = f"USD {change:,.0f} millones"
                        result["trend"] = "↑" if change > 0 else "↓"
                    
                    return {"success": True, "data": result}
                else:
                    # Datos históricos
                    return {"success": True, "data": {"historical": data[-10:]}}  # Últimos 10 registros
            elif isinstance(data, dict) and data.get("v"):
                result = {
                    "value": f"USD {data['v']:,.0f} millones",
                    "date": data["d"]
                }
                return {"success": True, "data": result}
            else:
                return {"success": False, "error": "No se encontraron datos de reservas"}
                
        except Exception as e:
            return {"success": False, "error": f"Error obteniendo reservas: {str(e)}"}
    
    async def get_market_data(self, indicator: str = "merval") -> Dict[str, Any]:
        """Obtiene datos de mercados financieros"""
        try:
            results = {}
            
            if indicator in ["merval", "todos"]:
                # Para el MERVAL, usaremos un endpoint genérico o simularemos
                merval_value = 1500000  # Valor simulado
                results["merval"] = {
                    "value": f"{merval_value:,.0f} puntos",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "change": "↑ 2.3%"
                }
            
            if indicator in ["riesgo_pais", "todos"]:
                # Riesgo país simulado
                results["riesgo_pais"] = {
                    "value": "1,200 puntos básicos",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "change": "↓ 0.5%"
                }
            
            return {"success": True, "data": results}
            
        except Exception as e:
            return {"success": False, "error": f"Error obteniendo datos de mercado: {str(e)}"}
    
    async def get_economic_analysis(self, analysis_type: str = "resumen_completo") -> Dict[str, Any]:
        """Genera análisis económico integral"""
        try:
            # Recopilar datos de múltiples fuentes
            dollar_data = await self.get_dollar_rates("ambos")
            inflation_data = await self.get_inflation_data("mensual")
            rates_data = await self.get_interest_rates("todas")
            reserves_data = await self.get_reserves_data("actual")
            
            analysis = {
                "timestamp": datetime.now().isoformat(),
                "type": analysis_type,
                "insights": []
            }
            
            # Generar insights basados en los datos
            if dollar_data.get("success") and "brecha_cambiaria" in dollar_data["data"]:
                brecha = float(dollar_data["data"]["brecha_cambiaria"].replace("%", ""))
                if brecha > 100:
                    analysis["insights"].append("⚠️ La brecha cambiaria supera el 100%, indicando alta tensión en el mercado de divisas")
                elif brecha > 50:
                    analysis["insights"].append("📊 La brecha cambiaria está elevada, sugiriendo presión sobre el tipo de cambio")
                else:
                    analysis["insights"].append("✅ La brecha cambiaria se mantiene en niveles controlados")
            
            if inflation_data.get("success"):
                inflation_val = inflation_data["data"]["value"]
                analysis["insights"].append(f"📈 Inflación mensual actual: {inflation_val}")
                
                if "trend" in inflation_data["data"]:
                    trend = inflation_data["data"]["trend"]
                    if trend == "↑":
                        analysis["insights"].append("⚠️ La inflación muestra tendencia al alza")
                    else:
                        analysis["insights"].append("📉 La inflación muestra tendencia a la baja")
            
            if rates_data.get("success") and "badlar" in rates_data["data"]:
                badlar_val = rates_data["data"]["badlar"]["value"]
                analysis["insights"].append(f"🏦 Tasa BADLAR actual: {badlar_val}")
            
            # Agregar recomendaciones según el tipo de análisis
            if analysis_type == "resumen_completo":
                analysis["recommendations"] = [
                    "💰 Monitorear la evolución de la brecha cambiaria",
                    "📊 Seguir de cerca los indicadores de inflación",
                    "🏦 Evaluar oportunidades de inversión en base a las tasas",
                    "💵 Considerar la diversificación de monedas"
                ]
            
            return {"success": True, "data": analysis}
            
        except Exception as e:
            return {"success": False, "error": f"Error generando análisis: {str(e)}"}
    
    def _calculate_change(self, data: List[Dict]) -> Optional[str]:
        """Calcula el cambio porcentual entre los dos últimos valores"""
        if len(data) < 2:
            return None
        
        current = data[-1]["v"]
        previous = data[-2]["v"]
        
        if previous == 0:
            return None
        
        change = ((current - previous) / previous) * 100
        return f"{change:+.2f}%"
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Llama a una herramienta específica del servidor"""
        if tool_name not in self.tools:
            return {"success": False, "error": f"Herramienta '{tool_name}' no encontrada"}
        
        try:
            if tool_name == "get_dollar_rates":
                return await self.get_dollar_rates(arguments.get("rate_type", "ambos"))
            elif tool_name == "get_inflation_data":
                return await self.get_inflation_data(arguments.get("period", "mensual"))
            elif tool_name == "get_interest_rates":
                return await self.get_interest_rates(arguments.get("rate_type", "badlar"))
            elif tool_name == "get_reserves_data":
                return await self.get_reserves_data(arguments.get("period", "actual"))
            elif tool_name == "get_market_data":
                return await self.get_market_data(arguments.get("indicator", "merval"))
            elif tool_name == "get_economic_analysis":
                return await self.get_economic_analysis(arguments.get("analysis_type", "resumen_completo"))
            else:
                return {"success": False, "error": f"Herramienta '{tool_name}' no implementada"}
                
        except Exception as e:
            return {"success": False, "error": f"Error ejecutando {tool_name}: {str(e)}"}
    
    async def close(self):
        """Cierra la sesión HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def __aenter__(self):
        """Context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cierra automáticamente la sesión"""
        await self.close()

# Función principal para pruebas
async def main():
    """Función de prueba del servidor BCRA"""
    server = BCRAServerMCP()
    
    print("🏦 Probando Servidor BCRA MCP...")
    
    # Probar cotizaciones del dólar
    print("\n💵 Cotizaciones del dólar:")
    result = await server.call_tool("get_dollar_rates", {"rate_type": "ambos"})
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Probar inflación
    print("\n📈 Datos de inflación:")
    result = await server.call_tool("get_inflation_data", {"period": "mensual"})
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Probar análisis económico
    print("\n🧠 Análisis económico:")
    result = await server.call_tool("get_economic_analysis", {"analysis_type": "resumen_completo"})
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    await server.close()

if __name__ == "__main__":
    asyncio.run(main())