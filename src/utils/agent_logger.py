#!/usr/bin/env python3
"""
Agent Logger - Sistema de logging estructurado para el agente conversacional
Registra eventos relacionados con el funcionamiento del agente principal
"""

import os
import sys
import json
import logging
from datetime import datetime
import structlog
from typing import Dict, Any, Optional

# Remove console handler from basic configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[]  # Remove the console handler
)

class AgentLogger:
    """Logger estructurado para el agente conversacional"""
    
    def __init__(self, agent_id: str = "main_agent"):
        """Inicializar logger con ID único"""
        self.agent_id = agent_id
        
        # Crear directorio de logs si no existe
        logs_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Configurar archivo de log
        log_file = os.path.join(logs_dir, f"agent_{datetime.now().strftime('%Y%m%d')}.log")
        
        # Configurar structlog
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer()
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
        )
        
        # Crear logger
        self.logger = structlog.get_logger(agent_id)
        
        # Agregar handler para archivo (solo archivo, sin consola)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        logging.getLogger().addHandler(file_handler)
        
        # Log de inicio (solo en archivo)
        self.info("Agent logger initialized", agent_id=self.agent_id)
    
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
    
    def log_initialization(self, success: bool, components: Dict[str, bool]):
        """Registrar inicialización del agente"""
        self.info(
            "Agent initialization", 
            success=success,
            components=components
        )
    
    def log_user_input(self, user_input: str, session_id: Optional[str] = None):
        """Registrar entrada del usuario"""
        self.info(
            "User input received", 
            user_input=user_input,
            session_id=session_id
        )
    
    def log_agent_response(self, response: str, session_id: Optional[str] = None):
        """Registrar respuesta del agente"""
        self.info(
            "Agent response sent", 
            response_length=len(response),
            response_preview=response[:100] + "..." if len(response) > 100 else response,
            session_id=session_id
        )
    
    def log_error(self, error_message: str, error_type: str, details: Dict[str, Any] = None):
        """Registrar error detallado"""
        self.error(
            "Agent error", 
            error_message=error_message,
            error_type=error_type,
            details=details or {}
        )
    
    def log_mcp_tools_initialized(self, tool_count: int, servers: Dict[str, int]):
        """Registrar inicialización de herramientas MCP"""
        self.info(
            "MCP tools initialized", 
            tool_count=tool_count,
            servers=servers
        )
    
    def log_openai_call(self, model: str, token_count: int = 0, success: bool = True):
        """Registrar llamada a OpenAI"""
        self.info(
            "OpenAI API call", 
            model=model,
            token_count=token_count,
            success=success
        )
    
    def log_function_call(self, function_name: str, success: bool, execution_time: float = 0):
        """Registrar llamada a función MCP"""
        self.info(
            "Function call", 
            function_name=function_name,
            success=success,
            execution_time=execution_time
        )
    
    def log_cleanup(self, success: bool = True):
        """Registrar limpieza de recursos"""
        self.info("Agent cleanup", success=success)