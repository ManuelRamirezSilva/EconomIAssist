#!/usr/bin/env python3
"""
Cliente MCP Mejorado - Gestión Automática con Registro de Servidores
Implementa descubrimiento automático y conexión dinámica de servidores MCP
"""

import asyncio
import json
import os
import subprocess
import sys
from typing import Dict, List, Any, Optional
import structlog
from dataclasses import dataclass

try:
    from .mcp_registry import get_mcp_registry, MCPServerSpec
except ImportError:
    # Cuando se ejecuta directamente, usar importación absoluta
    from mcp_registry import get_mcp_registry, MCPServerSpec

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
    
    def __init__(self, spec: MCPServerSpec):
        self.spec = spec
        self.name = spec.name
        self.process = None
        self.tools = {}
        self.resources = {}
        self.is_connected = False
        
    async def connect(self) -> bool:
        """Conecta al servidor MCP usando la especificación"""
        try:
            # Preparar entorno con variables dinámicas
            full_env = os.environ.copy()
            runtime_env = self.spec.get_runtime_env()
            full_env.update(runtime_env)
            
            logger.info(f"🔌 Conectando a servidor MCP: {self.spec.name}")
            logger.debug(f"   Comando: {' '.join(self.spec.command)}")
            logger.debug(f"   Env vars: {list(runtime_env.keys())}")
            
            # Iniciar proceso del servidor
            self.process = await asyncio.create_subprocess_exec(
                *self.spec.command,
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
                logger.info(f"✅ Conectado al servidor MCP: {self.spec.name}")
                self.is_connected = True
                
                # Descubrir herramientas disponibles
                await self._discover_tools()
                await self._discover_resources()
                
                return True
            else:
                logger.error(f"❌ Error conectando a {self.spec.name}: {response}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error conectando a {self.spec.name}: {e}")
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
            logger.info(f"🔌 Desconectado del servidor: {self.spec.name}")

class MCPManager:
    """Gestor automatizado de múltiples conexiones MCP con descubrimiento dinámico"""
    
    def __init__(self):
        self.connections: Dict[str, MCPServerConnection] = {}
        self.registry = get_mcp_registry()
        self.connection_stats = {}
    
    async def auto_connect_servers(self) -> Dict[str, bool]:
        """Conecta automáticamente a todos los servidores disponibles configurados para auto-connect"""
        auto_connect_specs = self.registry.get_auto_connect_servers()
        connection_results = {}
        
        logger.info(f"🚀 Iniciando auto-conexión de {len(auto_connect_specs)} servidores MCP...")
        
        # Conectar en orden de prioridad
        priority_order = self.registry.get_server_priorities()
        
        for server_name in priority_order:
            if server_name in auto_connect_specs:
                spec = auto_connect_specs[server_name]
                success = await self.connect_server(spec)
                connection_results[server_name] = success
                
                if success:
                    logger.info(f"✅ {server_name}: Conectado ({len(self.connections[server_name].tools)} herramientas)")
                else:
                    logger.warning(f"⚠️ {server_name}: Error de conexión")
        
        total_connected = sum(1 for success in connection_results.values() if success)
        logger.info(f"📊 Resumen: {total_connected}/{len(auto_connect_specs)} servidores conectados")
        
        return connection_results
    
    async def connect_server(self, spec: MCPServerSpec) -> bool:
        """Conecta a un servidor específico usando su especificación"""
        if spec.name in self.connections:
            logger.warning(f"⚠️ Servidor {spec.name} ya está conectado")
            return True
        
        connection = MCPServerConnection(spec)
        success = await connection.connect()
        
        if success:
            self.connections[spec.name] = connection
            self.connection_stats[spec.name] = {
                'connected_at': asyncio.get_event_loop().time(),
                'tools_count': len(connection.tools),
                'resources_count': len(connection.resources),
                'capabilities': spec.capabilities
            }
        
        return success
    
    async def connect_server_by_name(self, server_name: str) -> bool:
        """Conecta a un servidor por nombre (on-demand)"""
        available_specs = self.registry.discover_available_servers()
        
        if server_name not in available_specs:
            logger.error(f"❌ Servidor {server_name} no disponible")
            return False
        
        spec = available_specs[server_name]
        return await self.connect_server(spec)
    
    async def connect_servers_with_capability(self, capability: str) -> Dict[str, bool]:
        """Conecta a todos los servidores que tienen una capacidad específica"""
        matching_specs = self.registry.get_servers_by_capability(capability)
        results = {}
        
        logger.info(f"🔍 Conectando servidores con capacidad '{capability}'...")
        
        for server_name, spec in matching_specs.items():
            if server_name not in self.connections:
                success = await self.connect_server(spec)
                results[server_name] = success
        
        return results
    
    async def get_available_tools(self) -> Dict[str, List[str]]:
        """Obtiene lista de herramientas disponibles por servidor"""
        tools_by_server = {}
        
        for server_name, connection in self.connections.items():
            if connection.is_connected:
                tools_by_server[server_name] = list(connection.tools.keys())
        
        return tools_by_server
    
    async def call_tool_smart(self, capability: str, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Llama a una herramienta inteligentemente basándose en capacidades"""
        # Si no hay servidores con esa capacidad conectados, intentar conectar
        connected_with_capability = []
        for server_name, connection in self.connections.items():
            if connection.is_connected and capability in connection.spec.capabilities:
                connected_with_capability.append(server_name)
        
        if not connected_with_capability:
            logger.info(f"🔍 No hay servidores conectados con capacidad '{capability}', conectando...")
            await self.connect_servers_with_capability(capability)
            
            # Actualizar lista
            for server_name, connection in self.connections.items():
                if connection.is_connected and capability in connection.spec.capabilities:
                    connected_with_capability.append(server_name)
        
        # Intentar llamar la herramienta en los servidores apropiados
        for server_name in connected_with_capability:
            connection = self.connections[server_name]
            if tool_name in connection.tools:
                logger.info(f"🔧 Llamando {tool_name} en servidor {server_name}")
                return await connection.call_tool(tool_name, arguments)
        
        logger.error(f"❌ Herramienta {tool_name} no encontrada en servidores con capacidad {capability}")
        return None
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de conexiones MCP"""
        stats = {
            'total_servers': len(self.connections),
            'connected_servers': sum(1 for conn in self.connections.values() if conn.is_connected),
            'total_tools': sum(len(conn.tools) for conn in self.connections.values()),
            'servers_by_capability': {},
            'server_details': self.connection_stats
        }
        
        # Agrupar por capacidades
        for server_name, connection in self.connections.items():
            if connection.is_connected:
                for capability in connection.spec.capabilities:
                    if capability not in stats['servers_by_capability']:
                        stats['servers_by_capability'][capability] = []
                    stats['servers_by_capability'][capability].append(server_name)
        
        return stats
    
    async def disconnect_all(self):
        """Desconecta de todos los servidores"""
        logger.info(f"🔌 Desconectando {len(self.connections)} servidores MCP...")
        
        for connection in self.connections.values():
            await connection.disconnect()
        
        self.connections.clear()
        self.connection_stats.clear()
        logger.info("🔌 Desconectado de todos los servidores MCP")


# Función de prueba mejorada
async def test_mcp_manager():
    """Prueba el nuevo sistema MCP con descubrimiento automático"""
    print("🧪 Probando MCPManager mejorado con registro automático...")
    
    manager = MCPManager()
    
    try:
        # Auto-conectar servidores disponibles
        results = await manager.auto_connect_servers()
        print(f"📊 Resultados de auto-conexión: {results}")
        
        # Mostrar estadísticas
        stats = manager.get_connection_stats()
        print(f"\n📈 Estadísticas MCP:")
        print(f"   Servidores conectados: {stats['connected_servers']}/{stats['total_servers']}")
        print(f"   Total herramientas: {stats['total_tools']}")
        print(f"   Capacidades disponibles: {list(stats['servers_by_capability'].keys())}")
        
        # Probar búsqueda inteligente por capacidad
        if "web_search" in stats['servers_by_capability']:
            print(f"\n🔍 Probando búsqueda web inteligente...")
            result = await manager.call_tool_smart("web_search", "search", {
                "query": "tendencias financieras Argentina 2025",
                "max_results": 3
            })
            
            if result:
                print(f"✅ Búsqueda exitosa: {str(result)[:200]}...")
            else:
                print("❌ Error en búsqueda")
        
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
    
    finally:
        await manager.disconnect_all()

if __name__ == "__main__":
    asyncio.run(test_mcp_manager())