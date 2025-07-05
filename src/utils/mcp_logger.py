#!/usr/bin/env python3
"""
MCP Logger - Sistema de logging estructurado para servidores MCP
Registra eventos relacionados con la comunicación y funcionamiento de los servidores MCP
"""
import os
import sys
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import structlog

# Remove console handler from basic configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[]  # Remove the console handler
)

class MCPLogger:
    """Logger estructurado para servidores MCP"""
    
    def __init__(self, server_id: str = "mcp_manager"):
        """Inicializar logger con ID único"""
        self.server_id = server_id
        
        # Crear directorio de logs si no existe
        logs_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Configurar archivo de log
        log_file = os.path.join(logs_dir, f"mcp_{datetime.now().strftime('%Y%m%d')}.log")
        
        # Configurar structlog
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer()
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
        )
        
        # Crear logger
        self.logger = structlog.get_logger(server_id)
        
        # Agregar handler para archivo (solo archivo, sin consola)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        logging.getLogger().addHandler(file_handler)
        
        # Log de inicio (solo en archivo)
        self.info("MCP logger initialized", server_id=self.server_id)
    
    def info(self, message: str, **kwargs):
        """Registrar mensaje informativo"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Registrar advertencia"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Registrar error"""
        self.logger.error(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Registrar mensaje de depuración"""
        self.logger.debug(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Registrar error crítico"""
        self.logger.critical(message, **kwargs)
    
    def log_server_connection(self, server_name: str, success: bool, connection_time: float = 0):
        """Registrar conexión a servidor MCP"""
        self.info(
            "MCP server connection", 
            server_name=server_name,
            success=success,
            connection_time=connection_time
        )
    
    def log_server_disconnection(self, server_name: str, success: bool):
        """Registrar desconexión de servidor MCP"""
        self.info(
            "MCP server disconnection", 
            server_name=server_name,
            success=success
        )
    
    def log_tool_discovery(self, server_name: str, tools_count: int, tools: List[str]):
        """Registrar descubrimiento de herramientas"""
        self.info(
            "MCP tool discovery", 
            server_name=server_name,
            tools_count=tools_count,
            tools=tools
        )
    
    def log_resource_discovery(self, server_name: str, resources_count: int, resources: List[str]):
        """Registrar descubrimiento de recursos"""
        self.info(
            "MCP resource discovery", 
            server_name=server_name,
            resources_count=resources_count,
            resources=resources
        )
    
    def log_tool_call(self, server_name: str, tool_name: str, arguments: Dict[str, Any], 
                     success: bool, response_size: int = 0, execution_time: float = 0):
        """Registrar llamada a herramienta MCP"""
        # Sanear argumentos para evitar datos sensibles o demasiado largos
        safe_args = {}
        for k, v in arguments.items():
            if isinstance(v, str) and len(v) > 100:
                safe_args[k] = v[:100] + "..."
            elif "password" in k.lower() or "secret" in k.lower() or "key" in k.lower():
                safe_args[k] = "[REDACTED]"
            else:
                safe_args[k] = v
        
        self.info(
            "MCP tool call", 
            server_name=server_name,
            tool_name=tool_name,
            arguments=safe_args,
            success=success,
            response_size=response_size,
            execution_time=execution_time
        )
    
    def log_resource_read(self, server_name: str, resource_uri: str, success: bool, 
                         resource_size: int = 0):
        """Registrar lectura de recurso MCP"""
        self.info(
            "MCP resource read", 
            server_name=server_name,
            resource_uri=resource_uri,
            success=success,
            resource_size=resource_size
        )
    
    def log_json_rpc_error(self, server_name: str, method: str, error_code: int, 
                          error_message: str):
        """Registrar error JSON-RPC"""
        self.error(
            "MCP JSON-RPC error", 
            server_name=server_name,
            method=method,
            error_code=error_code,
            error_message=error_message
        )
    
    def log_connection_stats(self, stats: Dict[str, Any]):
        """Registrar estadísticas de conexiones MCP"""
        self.info(
            "MCP connection stats", 
            total_servers=stats.get('total_servers', 0),
            connected_servers=stats.get('connected_servers', 0),
            total_tools=stats.get('total_tools', 0),
            capabilities=list(stats.get('servers_by_capability', {}).keys())
        )
    
    def log_auto_connect(self, servers_attempted: int, servers_connected: int, 
                        server_results: Dict[str, bool]):
        """Registrar auto-conexión de servidores"""
        self.info(
            "MCP auto connect", 
            servers_attempted=servers_attempted,
            servers_connected=servers_connected,
            server_results=server_results
        )
    
    def log_capability_request(self, capability: str, servers_available: List[str], 
                              server_selected: str = None):
        """Registrar solicitud basada en capacidad"""
        self.info(
            "MCP capability request", 
            capability=capability,
            servers_available=servers_available,
            server_selected=server_selected
        )