#!/usr/bin/env python3
"""
Intent Logger - Sistema de logging estructurado para el parser de intenciones
Registra eventos relacionados con la detección y procesamiento de intenciones
"""
import os
import sys
import json
import logging
from datetime import datetime
import structlog
from typing import Dict, List, Any, Optional

# Remove console handler from basic configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[]  # Remove the console handler
)

class IntentLogger:
    """Logger estructurado para el parser de intenciones"""
    
    def __init__(self, parser_id: str = "main_parser"):
        """Inicializar logger con ID único"""
        self.parser_id = parser_id
        
        # Crear directorio de logs si no existe
        logs_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Configurar archivo de log
        log_file = os.path.join(logs_dir, f"intent_{datetime.now().strftime('%Y%m%d')}.log")
        
        # Configurar structlog
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer()
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
        )
        
        # Crear logger
        self.logger = structlog.get_logger(parser_id)
        
        # Agregar handler para archivo (solo archivo, sin consola)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        logging.getLogger().addHandler(file_handler)
        
        # Log de inicio (solo en archivo)
        self.info("Intent parser logger initialized", parser_id=self.parser_id)
    
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
    
    def log_parser_initialization(self, success: bool, azure_config: Dict[str, str]):
        """Registrar inicialización del parser"""
        # Ocultar información sensible
        sanitized_config = {k: "[REDACTED]" if "key" in k.lower() else v 
                           for k, v in azure_config.items()}
        
        self.info(
            "Intent parser initialization", 
            success=success,
            azure_config=sanitized_config
        )
    
    def log_intent_detection(self, user_input: str, detected_intents: Dict[str, Any], 
                            processing_time: float):
        """Registrar detección de intenciones"""
        self.info(
            "Intent detection", 
            user_input_length=len(user_input),
            user_input_preview=user_input[:50] + "..." if len(user_input) > 50 else user_input,
            detected_intents=detected_intents,
            processing_time=processing_time
        )
    
    def log_model_call(self, model: str, success: bool, processing_time: float):
        """Registrar llamada al modelo de detección de intenciones"""
        self.info(
            "Intent model call", 
            model=model,
            success=success,
            processing_time=processing_time
        )
    
    def log_intent_mapping(self, intent: str, mapped_capability: str = None, 
                          mapped_server: str = None):
        """Registrar mapeo de intención a capacidad/servidor"""
        self.info(
            "Intent mapping", 
            intent=intent,
            mapped_capability=mapped_capability,
            mapped_server=mapped_server
        )
    
    def log_multiple_intents(self, user_input: str, intents_count: int, intents: List[str]):
        """Registrar detección de múltiples intenciones"""
        self.info(
            "Multiple intents detected", 
            user_input_preview=user_input[:50] + "..." if len(user_input) > 50 else user_input,
            intents_count=intents_count,
            intents=intents
        )
    
    def log_parse_error(self, user_input: str, error_message: str, error_type: str):
        """Registrar error en parsing de intenciones"""
        self.error(
            "Intent parsing error", 
            user_input_preview=user_input[:50] + "..." if len(user_input) > 50 else user_input,
            error_message=error_message,
            error_type=error_type
        )
    
    def log_intent_confidence(self, intent: str, confidence: float):
        """Registrar confianza en la detección de intención"""
        self.info(
            "Intent confidence", 
            intent=intent,
            confidence=confidence
        )