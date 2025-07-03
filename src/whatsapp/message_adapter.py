#!/usr/bin/env python3
"""
Adaptador de mensajes de WhatsApp para EconomIAssist
Gestiona el contexto específico de WhatsApp y la integración con el agente conversacional
"""

import os
import sys
import json
from typing import Optional, Dict, Any
from datetime import datetime

# Agregar el directorio raíz al path para importaciones
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

import structlog

# Importar el agente conversacional
from src.agent.conversational_agent import ConversationalAgent

# Configurar logging
logger = structlog.get_logger(__name__)

class WhatsAppMessageAdapter:
    """
    Adaptador que procesa mensajes de WhatsApp y los integra con EconomIAssist
    """
    
    def __init__(self, agent: ConversationalAgent):
        """
        Inicializar el adaptador con el agente conversacional
        
        Args:
            agent: Instancia del agente conversacional de EconomIAssist
        """
        self.agent = agent
        self.whatsapp_context = {}
        
        logger.info("WhatsApp Message Adapter inicializado")
    
    async def process_whatsapp_message(
        self,
        message: str,
        from_jid: str,
        is_group: bool = False,
        sender_number: Optional[str] = None,
        timestamp: Optional[str] = None,
        message_id: Optional[str] = None,
        group_name: Optional[str] = None
    ) -> str:
        """
        Procesar un mensaje de WhatsApp y generar respuesta usando EconomIAssist
        
        Args:
            message: Texto del mensaje
            from_jid: ID del chat/grupo de WhatsApp
            is_group: Si es mensaje de grupo
            sender_number: Número del remitente
            timestamp: Timestamp del mensaje
            message_id: ID único del mensaje
            group_name: Nombre del grupo (si aplica)
            
        Returns:
            str: Respuesta generada por EconomIAssist
        """
        try:
            # Construir contexto enriquecido del mensaje
            enriched_message = self._build_enriched_message(
                message=message,
                from_jid=from_jid,
                is_group=is_group,
                sender_number=sender_number,
                timestamp=timestamp,
                message_id=message_id,
                group_name=group_name
            )
            
            # Procesar con el agente conversacional de EconomIAssist
            response = await self.agent.process_user_input(enriched_message)
            
            # Agregar contexto de WhatsApp si es necesario
            formatted_response = self._format_response_for_whatsapp(
                response=response,
                is_group=is_group,
                sender_number=sender_number
            )
            
            return formatted_response
            
        except Exception as e:
            # Solo log de errores críticos
            print(f"❌ Error en MessageAdapter para {sender_number}: {e}")
            
            # Respuesta de error amigable
            return "Disculpa, tuve un problema procesando tu mensaje. ¿Podrías intentar de nuevo?"
    
    def _build_enriched_message(
        self,
        message: str,
        from_jid: str,
        is_group: bool,
        sender_number: Optional[str],
        timestamp: Optional[str],
        message_id: Optional[str],
        group_name: Optional[str]
    ) -> str:
        """
        Construir mensaje enriquecido con contexto de WhatsApp para EconomIAssist
        
        El agente conversacional recibirá el contexto de WhatsApp pero procesará
        principalmente el mensaje original del usuario.
        """
        
        # Almacenar contexto para uso futuro
        context_key = sender_number or from_jid
        self.whatsapp_context[context_key] = {
            "from_jid": from_jid,
            "is_group": is_group,
            "sender_number": sender_number,
            "group_name": group_name,
            "last_message_time": timestamp,
            "message_id": message_id
        }
        
        # Para el agente, enviamos principalmente el mensaje del usuario
        # El contexto de WhatsApp se maneja internamente
        enriched_parts = []
        
        # Si es grupo, agregar contexto del grupo
        if is_group and group_name:
            enriched_parts.append(f"[Mensaje de grupo '{group_name}']")
        
        # Si es la primera vez que habla este usuario, agregar contexto
        if sender_number and not self._has_previous_context(sender_number):
            enriched_parts.append(f"[Usuario WhatsApp: {sender_number}]")
        
        # Agregar el mensaje principal
        enriched_parts.append(message)
        
        return " ".join(enriched_parts)
    
    def _has_previous_context(self, sender_number: str) -> bool:
        """
        Verificar si ya tenemos contexto previo de este usuario
        """
        return sender_number in self.whatsapp_context
    
    def _format_response_for_whatsapp(
        self,
        response: str,
        is_group: bool,
        sender_number: Optional[str]
    ) -> str:
        """
        Formatear respuesta para WhatsApp (opcional)
        
        Por ahora devolvemos la respuesta tal como la genera EconomIAssist,
        pero aquí podríamos agregar formato específico de WhatsApp si fuera necesario.
        """
        
        # Para mensajes de grupo, podríamos agregar mención si fuera necesario
        # Pero por ahora mantenemos la respuesta original
        
        return response
    
    def get_user_context(self, sender_number: str) -> Optional[Dict[str, Any]]:
        """
        Obtener contexto almacenado de un usuario específico
        """
        return self.whatsapp_context.get(sender_number)
    
    def clear_user_context(self, sender_number: str):
        """
        Limpiar contexto de un usuario específico
        """
        if sender_number in self.whatsapp_context:
            del self.whatsapp_context[sender_number]
            logger.info("Contexto de usuario limpiado", user=sender_number)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas del adaptador
        """
        return {
            "total_users": len(self.whatsapp_context),
            "users_with_context": list(self.whatsapp_context.keys()),
            "adapter_status": "active"
        }