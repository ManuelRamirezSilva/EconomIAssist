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
from dotenv import load_dotenv
import time

# Cargar variables de entorno desde .env
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(env_path, override=True)

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
            
            # Establecer directorio de trabajo como la raíz del proyecto
            project_root = os.path.join(os.path.dirname(__file__), '..', '..')
            project_root = os.path.abspath(project_root)
            
            logger.info(f"🔌 Conectando a servidor MCP: {self.spec.name}")
            logger.debug(f"   Comando: {' '.join(self.spec.command)}")
            logger.debug(f"   Env vars: {list(runtime_env.keys())}")
            logger.debug(f"   Directorio de trabajo: {project_root}")
            
            # Manejar contenedores Docker con --detach especialmente
            if "docker" in self.spec.command and "--detach" in self.spec.command:
                await self._handle_detached_container(full_env, project_root)
                # Para contenedores detached, conectar al proceso existente
                return await self._connect_to_existing_container()
            
            # Iniciar proceso del servidor normalmente con directorio de trabajo correcto
            self.process = await asyncio.create_subprocess_exec(
                *self.spec.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=full_env,
                cwd=project_root  # Establecer directorio de trabajo
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
                
                # Enviar mensaje de initialized para completar handshake
                initialized_notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
                await self._send_request(initialized_notification)
                
                # Esperar un poco para que el servidor procese el handshake
                await asyncio.sleep(0.1)
                
                self.is_connected = True
                
                # Descubrir herramientas disponibles (después del handshake completo)
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
            # Intentar leer múltiples líneas hasta encontrar JSON válido
            max_attempts = 5
            for attempt in range(max_attempts):
                line = await asyncio.wait_for(self.process.stdout.readline(), timeout=10.0)
                if line:
                    line_str = line.decode().strip()
                    
                    # Ignorar líneas vacías
                    if not line_str:
                        continue
                    
                    # Ignorar mensajes que claramente no son JSON-RPC
                    if (line_str.startswith("MCP") or 
                        line_str.startswith("Server") or 
                        line_str.startswith("Authentication") or
                        line_str.startswith("Calendar") or
                        "started" in line_str.lower()):
                        logger.debug(f"Ignorando mensaje de estado del servidor: {line_str}")
                        continue
                    
                    # Intentar parsear como JSON
                    try:
                        return json.loads(line_str)
                    except json.JSONDecodeError:
                        # Si no es JSON válido, continuar leyendo
                        logger.debug(f"Línea no es JSON válido, continuando: {line_str}")
                        continue
                else:
                    return None
            
            # Si llegamos aquí, no pudimos encontrar JSON válido
            logger.warning("No se pudo encontrar respuesta JSON válida después de múltiples intentos")
            return None
            
        except asyncio.TimeoutError:
            logger.error("Timeout leyendo respuesta del servidor")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error decodificando respuesta JSON: {e}")
            return None
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
                    # Eliminar log individual por herramienta - muy verboso
                    
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
                    # Eliminar log individual por recurso - muy verboso
                    
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
                if response and "error" in response:
                    # Log JSON-RPC error
                    try:
                        from ..utils.mcp_logger import MCPLogger
                        mcp_logger = MCPLogger(server_id=self.name)
                    except ImportError:
                        import sys
                        import os
                        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
                        from utils.mcp_logger import MCPLogger
                        mcp_logger = MCPLogger(server_id=self.name)
                    
                    error_code = response["error"].get("code", -1)
                    error_message = response["error"].get("message", "Unknown error")
                    
                    mcp_logger.log_json_rpc_error(
                        server_name=self.name,
                        method=tool_name,
                        error_code=error_code,
                        error_message=error_message
                    )
                
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

    async def _handle_detached_container(self, env, project_root):
        """Maneja contenedores Docker que usan --detach"""
        container_name = None
        
        # Extraer nombre del contenedor del comando
        if "--name" in self.spec.command:
            name_index = self.spec.command.index("--name") + 1
            if name_index < len(self.spec.command):
                container_name = self.spec.command[name_index]
        
        if container_name:
            # Verificar si el contenedor ya existe
            check_cmd = ["docker", "ps", "-q", "--filter", f"name={container_name}"]
            result = await asyncio.create_subprocess_exec(
                *check_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                cwd=project_root  # Usar directorio de trabajo correcto
            )
            stdout, _ = await result.communicate()
            
            if not stdout.strip():
                # El contenedor no existe, crearlo
                logger.info(f"🐳 Creando contenedor Docker: {container_name}")
                create_process = await asyncio.create_subprocess_exec(
                    *self.spec.command, env=env, cwd=project_root  # Usar directorio de trabajo correcto
                )
                await create_process.wait()
            else:
                logger.info(f"🐳 Contenedor Docker ya existe: {container_name}")
    
    async def _connect_to_existing_container(self) -> bool:
        """Conecta a un contenedor Docker existente usando configuración del YAML"""
        # Obtener configuración de Docker desde la especificación
        docker_config = getattr(self.spec, 'docker_config', {})
        
        if not docker_config:
            logger.error("No hay configuración Docker disponible para este servidor")
            return False
        
        container_name = docker_config.get('container_name')
        interactive_restart_command = docker_config.get('interactive_restart_command')
        restart_on_connect = docker_config.get('restart_on_connect', False)
        
        if not container_name or not interactive_restart_command:
            logger.error("Configuración Docker incompleta")
            return False
        
        try:
            if restart_on_connect:
                # Primero, parar el contenedor existente
                logger.info(f"🔄 Reiniciando contenedor {container_name} en modo interactivo...")
                
                stop_process = await asyncio.create_subprocess_exec(
                    "docker", "stop", container_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await stop_process.wait()
                
                remove_process = await asyncio.create_subprocess_exec(
                    "docker", "rm", container_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await remove_process.wait()
            
            # Crear nuevo contenedor usando comando del YAML
            self.process = await asyncio.create_subprocess_exec(
                *interactive_restart_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Esperar un poco para que el servidor se inicie
            await asyncio.sleep(2)
            
            # Enviar mensaje de inicialización MCP
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
                
                # Enviar mensaje de initialized para completar handshake
                initialized_notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
                await self._send_request(initialized_notification)
                
                # Esperar un poco para que el servidor procese el handshake
                await asyncio.sleep(0.1)
                
                self.is_connected = True
                
                # Descubrir herramientas disponibles (después del handshake completo)
                await self._discover_tools()
                await self._discover_resources()
                
                return True
            else:
                logger.error(f"❌ Error inicializando {self.spec.name}: {response}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error conectando al contenedor {container_name}: {e}")
            return False
    

class MCPManager:
    """Gestor automatizado de múltiples conexiones MCP con descubrimiento dinámico"""
    
    def __init__(self):
        self.connections: Dict[str, MCPServerConnection] = {}
        self.registry = get_mcp_registry()
        self.connection_stats = {}
        
        # Initialize MCP logger
        try:
            from ..utils.mcp_logger import MCPLogger
            self.mcp_logger = MCPLogger(server_id="mcp_manager")
        except ImportError:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
            from utils.mcp_logger import MCPLogger
            self.mcp_logger = MCPLogger(server_id="mcp_manager")
        
        self.mcp_logger.info("MCP manager instance created")
    
    async def auto_connect_servers(self) -> Dict[str, bool]:
        """Conecta automáticamente a todos los servidores disponibles configurados para auto-connect"""
        auto_connect_specs = self.registry.get_auto_connect_servers()
        connection_results = {}
        
        # Conectar en orden de prioridad
        priority_order = self.registry.get_server_priorities()
        
        for server_name in priority_order:
            if server_name in auto_connect_specs:
                spec = auto_connect_specs[server_name]
                success = await self.connect_server(spec)
                connection_results[server_name] = success
                
                if success:
                    tool_count = len(self.connections[server_name].tools)
                    print(f"✅ {server_name}: Conectado ({tool_count} herramientas)")
                else:
                    print(f"❌ {server_name}: Error de conexión")
    
        # Log auto-connect results
        connected_count = sum(1 for success in connection_results.values() if success)
        self.mcp_logger.log_auto_connect(
            servers_attempted=len(connection_results),
            servers_connected=connected_count,
            server_results=connection_results
        )
        
        return connection_results
    
    async def connect_server(self, spec: MCPServerSpec) -> bool:
        """Conecta a un servidor específico usando su especificación"""
        start_time = time.time()
        
        if spec.name in self.connections:
            self.mcp_logger.warning(f"Server already connected", server_name=spec.name)
            logger.warning(f"⚠️ Servidor {spec.name} ya está conectado")
            return True
        
        connection = MCPServerConnection(spec)
        success = await connection.connect()
        
        # Log connection result
        connection_time = time.time() - start_time
        self.mcp_logger.log_server_connection(
            server_name=spec.name,
            success=success,
            connection_time=connection_time
        )
        
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
                tools_list = list(connection.tools.keys())
                tools_by_server[server_name] = tools_list
                
                # Log tools discovery
                self.mcp_logger.log_tool_discovery(
                    server_name=server_name,
                    tools_count=len(tools_list),
                    tools=tools_list
                )

                # Log connection stats
                stats = self.get_connection_stats()
                self.mcp_logger.log_connection_stats(stats)
        
        return tools_by_server
    
    async def call_tool_smart(self, capability: str, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Llama a una herramienta inteligentemente basándose en capacidades"""
        # Si no hay servidores con esa capacidad conectados, intentar conectar
        connected_with_capability = []
        for server_name, connection in self.connections.items():
            if connection.is_connected and capability in connection.spec.capabilities:
                connected_with_capability.append(server_name)
        
        # Log capability request
        self.mcp_logger.log_capability_request(
            capability=capability,
            servers_available=connected_with_capability
        )
        
        if not connected_with_capability:
            logger.info(f"🔍 No hay servidores conectados con capacidad '{capability}', conectando...")
            await self.connect_servers_with_capability(capability)
            
            # Actualizar lista
            connected_with_capability = []
            for server_name, connection in self.connections.items():
                if connection.is_connected and capability in connection.spec.capabilities:
                    connected_with_capability.append(server_name)
            
            # Log updated capability servers
            self.mcp_logger.log_capability_request(
                capability=capability,
                servers_available=connected_with_capability
            )
        
        # Intentar llamar la herramienta en los servidores apropiados
        for server_name in connected_with_capability:
            connection = self.connections[server_name]
            if tool_name in connection.tools:
                logger.info(f"🔧 Llamando {tool_name} en servidor {server_name}")
                
                # Log selected server for capability
                self.mcp_logger.log_capability_request(
                    capability=capability,
                    servers_available=connected_with_capability,
                    server_selected=server_name
                )
                
                start_time = time.time()
                result = await connection.call_tool(tool_name, arguments)
                
                # Log tool call
                execution_time = time.time() - start_time
                success = result is not None
                response_size = len(str(result)) if result else 0
                
                self.mcp_logger.log_tool_call(
                    server_name=server_name,
                    tool_name=tool_name,
                    arguments=arguments,
                    success=success,
                    response_size=response_size,
                    execution_time=execution_time
                )
                
                return result
        
        # Log failure to find tool
        self.mcp_logger.error(f"Tool not found for capability", 
                             capability=capability, 
                             tool_name=tool_name)
        
        logger.error(f"❌ Herramienta {tool_name} no encontrada en servidores con capacidad {capability}")
        return None
    
    async def call_tool_by_function_name(self, function_name: str, params: dict) -> Any:
        """Llama una herramienta basándose en el nombre completo de la función (agnóstico)"""
        start_time = time.time()
        
        for server_name, connection in self.connections.items():
            if function_name.startswith(f"{server_name}_"):
                tool_name = function_name[len(server_name) + 1:]
                
                result = await connection.call_tool(tool_name, params)
                
                # Log tool call
                execution_time = time.time() - start_time
                response_size = len(str(result)) if result else 0
                success = result is not None
                
                self.mcp_logger.log_tool_call(
                    server_name=server_name,
                    tool_name=tool_name,
                    arguments=params,
                    success=success,
                    response_size=response_size,
                    execution_time=execution_time
                )
                
                if not success:
                    self.mcp_logger.error(f"Tool call failed", 
                                         server_name=server_name, 
                                         tool_name=tool_name)
                
                return result
        
        error_msg = f"No se encontró servidor para la función: {function_name}"
        self.mcp_logger.error(error_msg)
        
        raise ValueError(error_msg)
    
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
        
        for server_name, connection in self.connections.items():
            # Log server disconnection
            self.mcp_logger.log_server_disconnection(
                server_name=server_name,
                success=True
            )
            
            await connection.disconnect()
        
        # Log connection stats before clearing
        if self.connections:
            self.mcp_logger.log_connection_stats(self.get_connection_stats())
        
        self.connections.clear()
        self.connection_stats.clear()
        
        # Log disconnection complete
        self.mcp_logger.info("Disconnected from all MCP servers")
        
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