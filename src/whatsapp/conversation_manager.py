#!/usr/bin/env python3
"""
Gestor Conversacional Inteligente para WhatsApp
Implementa técnicas de agrupamiento temporal y respuestas humanas
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import structlog

# Configurar logging
logger = structlog.get_logger(__name__)

class ConversationManager:
    """
    Gestor que agrupa mensajes temporalmente y genera respuestas humanas
    """
    
    def __init__(self, window_seconds: int = 5, max_response_length: int = 1000):
        """
        Inicializar el gestor conversacional
        
        Args:
            window_seconds: Ventana temporal para agrupar mensajes (default: 5s)
            max_response_length: Longitud máxima antes de dividir respuesta
        """
        self.window_seconds = window_seconds
        self.max_response_length = max_response_length
        
        # Buffer de mensajes por usuario
        self.message_buffers: Dict[str, List[Dict]] = {}
        
        # Timers para procesar mensajes agrupados
        self.pending_timers: Dict[str, asyncio.Task] = {}
        
        # Callback para procesar mensajes agrupados
        self.process_callback = None
        
        logger.info("Conversation Manager inicializado", 
                   window_seconds=window_seconds,
                   max_response_length=max_response_length)
    
    def set_process_callback(self, callback):
        """
        Establecer callback para procesar mensajes agrupados
        
        Args:
            callback: Función async que procesa el mensaje agrupado
        """
        self.process_callback = callback
    
    async def add_message(self, user_id: str, message_data: Dict) -> bool:
        """
        Agregar mensaje al buffer temporal
        
        Args:
            user_id: Identificador del usuario (sender_number)
            message_data: Datos completos del mensaje
            
        Returns:
            bool: True si el mensaje fue agregado al buffer (no procesado aún)
        """
        current_time = time.time()
        
        # Agregar timestamp al mensaje
        message_data['buffer_timestamp'] = current_time
        
        # Inicializar buffer si no existe
        if user_id not in self.message_buffers:
            self.message_buffers[user_id] = []
        
        # Agregar mensaje al buffer
        self.message_buffers[user_id].append(message_data)
        
        logger.info("Mensaje agregado al buffer",
                   user_id=user_id,
                   buffer_size=len(self.message_buffers[user_id]),
                   message_preview=message_data.get('message', '')[:30])
        
        # Cancelar timer anterior si existe
        if user_id in self.pending_timers:
            self.pending_timers[user_id].cancel()
        
        # Crear nuevo timer para procesar mensajes agrupados
        self.pending_timers[user_id] = asyncio.create_task(
            self._delayed_process(user_id)
        )
        
        return True
    
    async def _delayed_process(self, user_id: str):
        """
        Procesar mensajes después de la ventana temporal
        
        Args:
            user_id: Identificador del usuario
        """
        try:
            # Esperar la ventana temporal
            await asyncio.sleep(self.window_seconds)
            
            # Obtener mensajes del buffer
            messages = self.message_buffers.get(user_id, [])
            
            if not messages:
                return
            
            # Limpiar buffer
            self.message_buffers[user_id] = []
            
            # Limpiar timer
            if user_id in self.pending_timers:
                del self.pending_timers[user_id]
            
            # Agrupar mensajes en contexto conversacional
            grouped_context = self._group_messages(messages)
            
            logger.info("Procesando mensajes agrupados",
                       user_id=user_id,
                       message_count=len(messages),
                       grouped_text_length=len(grouped_context['combined_message']))
            
            # Procesar con callback si está configurado
            if self.process_callback:
                await self.process_callback(user_id, grouped_context)
                
        except asyncio.CancelledError:
            # Timer cancelado por nuevo mensaje
            logger.debug("Timer cancelado por nuevo mensaje", user_id=user_id)
        except Exception as e:
            logger.error("Error procesando mensajes agrupados",
                        user_id=user_id, error=str(e))
    
    def _group_messages(self, messages: List[Dict]) -> Dict:
        """
        Agrupar múltiples mensajes en contexto conversacional único
        
        Args:
            messages: Lista de mensajes a agrupar
            
        Returns:
            Dict: Contexto agrupado con mensaje combinado y metadata
        """
        if not messages:
            return {}
        
        # Usar el último mensaje como base
        base_message = messages[-1]
        
        # Combinar textos de mensajes
        message_texts = [msg.get('message', '') for msg in messages]
        combined_message = ' '.join(message_texts).strip()
        
        # Detectar patrones conversacionales
        conversation_pattern = self._detect_conversation_pattern(message_texts)
        
        return {
            'combined_message': combined_message,
            'individual_messages': message_texts,
            'message_count': len(messages),
            'conversation_pattern': conversation_pattern,
            'time_span_seconds': messages[-1]['buffer_timestamp'] - messages[0]['buffer_timestamp'],
            'base_metadata': {
                'from_jid': base_message.get('from_jid'),
                'is_group': base_message.get('is_group', False),
                'sender_number': base_message.get('sender_number'),
                'group_name': base_message.get('group_name'),
                'timestamp': base_message.get('timestamp'),
                'message_id': base_message.get('message_id')
            }
        }
    
    def _detect_conversation_pattern(self, messages: List[str]) -> str:
        """
        Detectar el patrón conversacional de los mensajes
        
        Args:
            messages: Lista de textos de mensajes
            
        Returns:
            str: Tipo de patrón detectado
        """
        if len(messages) == 1:
            return "single_message"
        
        # Detectar mensajes cortos secuenciales
        if all(len(msg) < 20 for msg in messages):
            return "rapid_short_messages"
        
        # Detectar continuación de pensamiento
        if any(msg.lower().startswith(('y ', 'pero ', 'aunque ', 'además ')) for msg in messages[1:]):
            return "thought_continuation"
        
        # Detectar corrección/aclaración
        if any('digo' in msg.lower() or 'quise decir' in msg.lower() for msg in messages):
            return "correction"
        
        # Detectar cambio de tema
        financial_keywords = ['dinero', 'gasto', 'sueldo', 'finanzas', 'ahorro', 'banco']
        has_financial = any(any(kw in msg.lower() for kw in financial_keywords) for msg in messages)
        non_financial = any(not any(kw in msg.lower() for kw in financial_keywords) for msg in messages)
        
        if has_financial and non_financial:
            return "topic_change"
        
        return "sequential_messages"
    
    def split_response_human_like(self, response: str) -> List[str]:
        """
        Dividir respuesta larga en partes humanas
        
        Args:
            response: Respuesta completa a dividir
            
        Returns:
            List[str]: Lista de partes de respuesta
        """
        if len(response) <= self.max_response_length:
            return [response]
        
        parts = []
        current_part = ""
        
        # Dividir por párrafos primero
        paragraphs = response.split('\n\n')
        
        for paragraph in paragraphs:
            # Si agregar este párrafo excede el límite
            if len(current_part + paragraph) > self.max_response_length:
                # Si hay contenido acumulado, guardarlo
                if current_part.strip():
                    parts.append(current_part.strip())
                    current_part = ""
                
                # Si el párrafo mismo es muy largo, dividirlo por oraciones
                if len(paragraph) > self.max_response_length:
                    sentences = paragraph.split('. ')
                    for sentence in sentences:
                        if len(current_part + sentence) > self.max_response_length:
                            if current_part.strip():
                                parts.append(current_part.strip())
                                current_part = ""
                        current_part += sentence + ". "
                else:
                    current_part = paragraph
            else:
                current_part += "\n\n" + paragraph if current_part else paragraph
        
        # Agregar parte final
        if current_part.strip():
            parts.append(current_part.strip())
        
        # Agregar indicadores humanos
        if len(parts) > 1:
            for i, part in enumerate(parts):
                if i == 0:
                    parts[i] = part
                elif i == len(parts) - 1:
                    parts[i] = f"...y para terminar: {part}"
                else:
                    parts[i] = f"...continuando: {part}"
        
        return parts
    
    def should_respond_to_pattern(self, conversation_pattern: str, combined_message: str) -> bool:
        """
        Determinar si se debe responder basado en el patrón conversacional
        
        Args:
            conversation_pattern: Patrón detectado
            combined_message: Mensaje combinado
            
        Returns:
            bool: True si debe responder
        """
        # Patrones que NO requieren respuesta
        if conversation_pattern == "topic_change":
            # Si cambia a tema no financiero, podría no responder
            non_financial_endings = ['jodele', 'marido', 'esposo', 'deja', 'para']
            if any(ending in combined_message.lower() for ending in non_financial_endings):
                return False
        
        if conversation_pattern == "rapid_short_messages":
            # Para mensajes muy cortos como "jajaja", "ok", "bueno"
            short_non_responses = ['jajaja', 'jaja', 'ok', 'bueno', 'ahora']
            if combined_message.lower().strip() in short_non_responses:
                return False
        
        return True
    
    async def cleanup_user(self, user_id: str):
        """
        Limpiar buffer y timers de un usuario específico
        
        Args:
            user_id: Identificador del usuario
        """
        # Cancelar timer pendiente
        if user_id in self.pending_timers:
            self.pending_timers[user_id].cancel()
            del self.pending_timers[user_id]
        
        # Limpiar buffer
        if user_id in self.message_buffers:
            del self.message_buffers[user_id]
        
        logger.info("Usuario limpiado del Conversation Manager", user_id=user_id)