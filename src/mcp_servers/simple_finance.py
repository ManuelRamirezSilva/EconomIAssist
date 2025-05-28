#!/usr/bin/env python3
"""
Servidor MCP Simple - Cotizaciones Argentina
Implementa cotización del dólar y análisis financiero básico
"""

import asyncio
import json
import sys
from typing import Any, Dict
import httpx

class SimpleMCPServer:
    """Servidor MCP simple para cotizaciones argentinas"""
    
    def __init__(self):
        self.tools = {
            "get_dollar_price": {
                "description": "Obtiene el precio actual del dólar en Argentina",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["oficial", "blue", "mep", "ccl"],
                            "description": "Tipo de cotización del dólar"
                        }
                    },
                    "required": ["type"]
                }
            },
            "financial_advice": {
                "description": "Proporciona consejos financieros básicos",
                "input_schema": {
                    "type": "object", 
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Tema financiero sobre el cual dar consejo"
                        }
                    },
                    "required": ["topic"]
                }
            }
        }
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Maneja una petición JSON-RPC"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {"listChanged": False},
                            "resources": {"subscribe": False, "listChanged": False}
                        },
                        "serverInfo": {
                            "name": "simple-finance-mcp",
                            "version": "1.0.0"
                        }
                    }
                }
            
            elif method == "tools/list":
                tools_list = []
                for name, spec in self.tools.items():
                    tools_list.append({
                        "name": name,
                        "description": spec["description"],
                        "inputSchema": spec["input_schema"]
                    })
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": tools_list}
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "get_dollar_price":
                    result = await self._get_dollar_price(arguments.get("type", "blue"))
                elif tool_name == "financial_advice":
                    result = await self._get_financial_advice(arguments.get("topic", "general"))
                else:
                    raise Exception(f"Herramienta desconocida: {tool_name}")
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": result}]
                    }
                }
            
            else:
                raise Exception(f"Método no soportado: {method}")
                
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
    
    async def _get_dollar_price(self, dollar_type: str) -> str:
        """Obtiene el precio del dólar desde una API pública"""
        try:
            async with httpx.AsyncClient() as client:
                # API pública de dólar argentina
                response = await client.get("https://api.bluelytics.com.ar/v2/latest")
                data = response.json()
                
                prices = {
                    "oficial": f"${data['oficial']['value_sell']:.2f}",
                    "blue": f"${data['blue']['value_sell']:.2f}",
                    "mep": f"${data.get('mep', {}).get('value_sell', 'N/A')}",
                    "ccl": f"${data.get('ccl', {}).get('value_sell', 'N/A')}"
                }
                
                return f"💰 Dólar {dollar_type.upper()}: {prices.get(dollar_type, 'N/A')} ARS\n📊 Actualizado: {data.get('last_update', 'N/A')}"
                
        except Exception as e:
            return f"❌ Error obteniendo cotización: {str(e)}\n💡 Precio aproximado del dólar blue: $1350 ARS"
    
    async def _get_financial_advice(self, topic: str) -> str:
        """Proporciona consejos financieros básicos"""
        advice_db = {
            "ahorro": "💰 Consejos para ahorrar:\n• Regla 50/30/20: 50% gastos necesarios, 30% gustos, 20% ahorro\n• Automatiza tus ahorros\n• Evita compras impulsivas\n• Busca ofertas y descuentos",
            "inversion": "📈 Consejos de inversión:\n• Diversifica tu cartera\n• Invierte solo lo que puedas permitirte perder\n• Considera instrumentos en pesos y dólares\n• Educate financieramente antes de invertir",
            "dolar": "💵 Sobre el dólar:\n• Considera tener parte de tus ahorros en dólares\n• Evalúa instrumentos como FCI en dólares\n• No pongas todo en una sola moneda\n• Mantente informado sobre la situación económica",
            "deuda": "💳 Manejo de deudas:\n• Prioriza deudas con mayor tasa de interés\n• Considera consolidar deudas\n• Evita el pago mínimo de tarjetas\n• Negocia planes de pago si es necesario"
        }
        
        for key, advice in advice_db.items():
            if key in topic.lower():
                return advice
        
        return "💡 Consejos financieros generales:\n• Lleva un presupuesto mensual\n• Ten un fondo de emergencia\n• Invierte en tu educación financiera\n• Consulta con asesores profesionales para decisiones importantes"

    async def run(self):
        """Ejecuta el servidor MCP"""
        while True:
            try:
                # Leer petición desde stdin
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                request = json.loads(line.strip())
                response = await self.handle_request(request)
                
                # Enviar respuesta a stdout
                print(json.dumps(response))
                sys.stdout.flush()
                
            except json.JSONDecodeError:
                continue
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()

if __name__ == "__main__":
    server = SimpleMCPServer()
    asyncio.run(server.run())