#!/usr/bin/env python3
"""
Cliente MCP Real para conectar con servidores MCP externos
Implementa el protocolo JSON-RPC para comunicación con servidores MCP
"""

import asyncio
import json
import os
import subprocess
import sys
from typing import Dict, List, Any, Optional
import structlog
from dataclasses import dataclass

logger = structlog.get_logger()

@dataclass
class MCPTool:
    """Representa una herramienta MCP disponible"""
    name: str
    description: str
    input_schema: Dict[str, Any]

@dataclass 
class MCPResource:
    """Representa un recurso MCP disponible"""
    uri: str
    name: str
    description: str
    mime_type: str

class MCPServerConnection:
    """Conexión a un servidor MCP específico"""
    
    def __init__(self, name: str, command: List[str], env: Optional[Dict[str, str]] = None):
        self.name = name
        self.command = command
        self.env = env or {}
        self.process = None
        self.tools = {}
        self.resources = {}
        self.is_connected = False
        
    async def connect(self) -> bool:
        """Conecta al servidor MCP"""
        try:
            # Preparar entorno
            full_env = os.environ.copy()
            full_env.update(self.env)
            
            # Iniciar proceso del servidor
            self.process = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=full_env
            )
            
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
            
            await self._send_request(init_request)
            response = await self._read_response()
            
            if response and "result" in response:
                logger.info(f"✅ Conectado al servidor MCP: {self.name}")
                self.is_connected = True
                
                # Descubrir herramientas disponibles
                await self._discover_tools()
                await self._discover_resources()
                
                return True
            else:
                logger.error(f"❌ Error conectando a {self.name}: {response}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error conectando a {self.name}: {e}")
            return False
    
    async def _send_request(self, request: Dict[str, Any]):
        """Envía una petición JSON-RPC al servidor"""
        if not self.process or not self.process.stdin:
            raise Exception("Servidor no conectado")
            
        message = json.dumps(request) + "\n"
        self.process.stdin.write(message.encode())
        await self.process.stdin.drain()
    
    async def _read_response(self) -> Optional[Dict[str, Any]]:
        """Lee una respuesta JSON-RPC del servidor"""
        if not self.process or not self.process.stdout:
            return None
            
        try:
            line = await self.process.stdout.readline()
            if line:
                return json.loads(line.decode().strip())
        except json.JSONDecodeError as e:
            logger.error(f"Error decodificando respuesta JSON: {e}")
        except Exception as e:
            logger.error(f"Error leyendo respuesta: {e}")
            
        return None
    
    async def _discover_tools(self):
        """Descubre herramientas disponibles en el servidor"""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            }
            
            await self._send_request(request)
            response = await self._read_response()
            
            if response and "result" in response:
                tools_list = response["result"].get("tools", [])
                for tool in tools_list:
                    mcp_tool = MCPTool(
                        name=tool["name"],
                        description=tool.get("description", ""),
                        input_schema=tool.get("inputSchema", {})
                    )
                    self.tools[tool["name"]] = mcp_tool
                    logger.info(f"🔧 Herramienta descubierta: {tool['name']}")
                    
        except Exception as e:
            logger.error(f"Error descubriendo herramientas: {e}")
    
    async def _discover_resources(self):
        """Descubre recursos disponibles en el servidor"""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "resources/list"
            }
            
            await self._send_request(request)
            response = await self._read_response()
            
            if response and "result" in response:
                resources_list = response["result"].get("resources", [])
                for resource in resources_list:
                    mcp_resource = MCPResource(
                        uri=resource["uri"],
                        name=resource.get("name", ""),
                        description=resource.get("description", ""),
                        mime_type=resource.get("mimeType", "text/plain")
                    )
                    self.resources[resource["uri"]] = mcp_resource
                    logger.info(f"📄 Recurso descubierto: {resource['uri']}")
                    
        except Exception as e:
            logger.error(f"Error descubriendo recursos: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Llama a una herramienta del servidor MCP"""
        if not self.is_connected:
            logger.error("Servidor no conectado")
            return None
            
        if tool_name not in self.tools:
            logger.error(f"Herramienta {tool_name} no disponible")
            return None
        
        try:
            request = {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            await self._send_request(request)
            response = await self._read_response()
            
            if response and "result" in response:
                return response["result"]
            else:
                logger.error(f"Error llamando herramienta {tool_name}: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error llamando herramienta {tool_name}: {e}")
            return None
    
    async def read_resource(self, uri: str) -> Optional[str]:
        """Lee un recurso del servidor MCP"""
        if not self.is_connected:
            logger.error("Servidor no conectado")
            return None
            
        try:
            request = {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "resources/read",
                "params": {
                    "uri": uri
                }
            }
            
            await self._send_request(request)
            response = await self._read_response()
            
            if response and "result" in response:
                contents = response["result"].get("contents", [])
                if contents:
                    return contents[0].get("text", "")
            
            return None
            
        except Exception as e:
            logger.error(f"Error leyendo recurso {uri}: {e}")
            return None
    
    async def disconnect(self):
        """Desconecta del servidor MCP"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.is_connected = False
            logger.info(f"🔌 Desconectado del servidor: {self.name}")

class MCPManager:
    """Gestor de múltiples conexiones MCP"""
    
    def __init__(self):
        self.connections = {}
        
    async def connect_tavily_server(self) -> bool:
        """Conecta al servidor Tavily MCP"""
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            logger.error("❌ TAVILY_API_KEY no configurada")
            return False
        
        # Comando para ejecutar el servidor Tavily
        command = ["npx", "tavily-mcp"]
        env = {"TAVILY_API_KEY": tavily_api_key}
        
        connection = MCPServerConnection("tavily", command, env)
        success = await connection.connect()
        
        if success:
            self.connections["tavily"] = connection
            logger.info(f"🌐 Servidor Tavily MCP conectado con {len(connection.tools)} herramientas")
            return True
        
        return False
    
    async def search_web(self, query: str, max_results: int = 5) -> Optional[str]:
        """Busca en la web usando Tavily"""
        if "tavily" not in self.connections:
            logger.error("Servidor Tavily no conectado")
            return None
        
        connection = self.connections["tavily"]
        
        # Buscar herramienta de búsqueda web
        search_tool = None
        for tool_name in connection.tools:
            if "search" in tool_name.lower() or "web" in tool_name.lower():
                search_tool = tool_name
                break
        
        if not search_tool:
            logger.error("Herramienta de búsqueda no encontrada en Tavily")
            return None
        
        result = await connection.call_tool(search_tool, {
            "query": query,
            "max_results": max_results
        })
        
        if result:
            # Formatear resultados para el LLM
            content = result.get("content", [])
            if isinstance(content, list) and content:
                return content[0].get("text", str(result))
            return str(result)
        
        return None
    
    async def get_available_tools(self) -> Dict[str, List[str]]:
        """Obtiene lista de herramientas disponibles por servidor"""
        tools_by_server = {}
        
        for server_name, connection in self.connections.items():
            if connection.is_connected:
                tools_by_server[server_name] = list(connection.tools.keys())
        
        return tools_by_server
    
    async def disconnect_all(self):
        """Desconecta de todos los servidores"""
        for connection in self.connections.values():
            await connection.disconnect()
        
        self.connections.clear()
        logger.info("🔌 Desconectado de todos los servidores MCP")

# Prueba del cliente MCP
async def test_mcp_client():
    """Prueba la conexión MCP con Tavily"""
    print("🧪 Probando cliente MCP real con Tavily...")
    
    manager = MCPManager()
    
    try:
        # Conectar a Tavily
        success = await manager.connect_tavily_server()
        
        if success:
            print("✅ Conexión exitosa con Tavily MCP")
            
            # Mostrar herramientas disponibles
            tools = await manager.get_available_tools()
            print(f"🔧 Herramientas disponibles: {tools}")
            
            # Probar búsqueda web
            print("\n🔍 Probando búsqueda web...")
            result = await manager.search_web("latest financial trends 2025", max_results=3)
            
            if result:
                print(f"📊 Resultado de búsqueda:\n{result[:500]}...")
            else:
                print("❌ No se pudo realizar la búsqueda")
        else:
            print("❌ Error conectando con Tavily MCP")
    
    except Exception as e:
        print(f"❌ Error en prueba MCP: {e}")
    
    finally:
        await manager.disconnect_all()

if __name__ == "__main__":
    asyncio.run(test_mcp_client())