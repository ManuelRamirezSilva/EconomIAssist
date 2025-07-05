#!/usr/bin/env python3
"""
Servidor HTTP para recibir mensajes de WhatsApp Bridge
Integra con el ConversationalAgent existente de EconomIAssist + Conversation Manager
"""

import asyncio
import os
import sys
import logging
from typing import Optional, List, Dict
from datetime import datetime
import aiohttp
import json

# Agregar el directorio raíz al path para importaciones
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
import uvicorn
from dotenv import load_dotenv
from openai import AzureOpenAI

# Configuración para el modelo de refinamiento (usando Azure OpenAI como en intentParser)
AZURE_OPENAI_API_BASE = os.getenv("AZURE_OPENAI_API_BASE", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")

# Filtro personalizado para reducir logs HTTP repetitivos
class HttpPollingFilter(logging.Filter):
    """Filtro para suprimir logs HTTP de polling frecuente"""
    
    def filter(self, record):
        # Suprimir logs de polling a /whatsapp/pending-responses
        if hasattr(record, 'getMessage'):
            message = record.getMessage()
            if 'GET /whatsapp/pending-responses' in message and '200 OK' in message:
                return False
        return True

# Importar el agente conversacional existente y nuevo conversation manager
from src.agent.conversational_agent import ConversationalAgent
from src.whatsapp.message_adapter import WhatsAppMessageAdapter
from src.whatsapp.conversation_manager import ConversationManager

# Cargar variables de entorno
load_dotenv()

# Configuración
WHATSAPP_SERVER_HOST = os.getenv("WHATSAPP_SERVER_HOST", "localhost")
WHATSAPP_SERVER_PORT = int(os.getenv("WHATSAPP_SERVER_PORT", "8000"))

# Crear instancia de FastAPI
app = FastAPI(
    title="EconomIAssist WhatsApp Server v2.0",
    description="Servidor HTTP que recibe mensajes de WhatsApp Bridge con Conversation Manager inteligente",
    version="2.0.0"
)

# Variables globales
agent: Optional[ConversationalAgent] = None
adapter: Optional[WhatsAppMessageAdapter] = None
conversation_manager: Optional[ConversationManager] = None
azure_client: Optional[AzureOpenAI] = None
pending_responses: List[Dict] = []  # Cola de respuestas para el WhatsApp Bridge
processed_messages: set = set()  # Cache de IDs de mensajes ya procesados (para evitar duplicados)

@app.on_event("startup")
async def startup_event():
    """Inicializar el agente conversacional y conversation manager al arrancar el servidor"""
    global agent, adapter, conversation_manager, azure_client
    
    # Configurar filtro para logs HTTP
    uvicorn_logger = logging.getLogger("uvicorn.access")
    uvicorn_logger.addFilter(HttpPollingFilter())
    
    print("🚀 Iniciando EconomIAssist WhatsApp Server v2.0...")
    
    try:
        # Inicializar el agente conversacional
        agent = ConversationalAgent()
        initialized = await agent.initialize()
        
        if not initialized:
            raise Exception("No se pudo inicializar el agente conversacional")
        
        # Inicializar el adaptador de mensajes
        adapter = WhatsAppMessageAdapter(agent)
        
        # Inicializar el Conversation Manager
        conversation_manager = ConversationManager(
            window_seconds=5,  # 5 segundos para agrupar mensajes
            max_response_length=1000  # Máximo 1000 caracteres por parte
        )
        
        # Configurar callback para procesar mensajes agrupados
        conversation_manager.set_process_callback(process_grouped_messages)
        
        # Inicializar cliente de Azure OpenAI para refinamiento
        if AZURE_OPENAI_API_BASE and AZURE_OPENAI_API_KEY:
            try:
                azure_client = AzureOpenAI(
                    azure_endpoint=AZURE_OPENAI_API_BASE,
                    api_key=AZURE_OPENAI_API_KEY,
                    api_version=AZURE_OPENAI_API_VERSION
                )
                print("✅ Cliente Azure OpenAI inicializado correctamente")
            except Exception as e:
                print(f"⚠️ Error inicializando cliente Azure OpenAI: {e}")
                azure_client = None
        
        print("✅ EconomIAssist WhatsApp Server v2.0 iniciado exitosamente")
        print(f"📡 Escuchando en: http://{WHATSAPP_SERVER_HOST}:{WHATSAPP_SERVER_PORT}")
        print("🔗 Endpoint WhatsApp: /whatsapp/message")
        print("🧠 Conversation Manager: Activado (ventana: 5s)")
        
        # Log de estado del refinamiento de respuestas
        if AZURE_OPENAI_API_BASE and AZURE_OPENAI_API_KEY:
            print("🧰 Refinamiento de respuestas: ACTIVADO (usando Azure OpenAI)")
        else:
            print("⚠️ Refinamiento de respuestas: DESACTIVADO (variables de entorno Azure no configuradas)")
        
    except Exception as e:
        print(f"❌ Error iniciando servidor: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Limpiar recursos al cerrar el servidor"""
    global agent
    
    print("🛑 Cerrando EconomIAssist WhatsApp Server...")
    
    if agent:
        try:
            await agent.cleanup()
            print("✅ Agente conversacional cerrado correctamente")
        except Exception as e:
            print(f"⚠️ Error cerrando agente: {e}")

async def process_grouped_messages(user_id: str, grouped_context: dict):
    """
    Callback para procesar mensajes agrupados por el Conversation Manager
    
    Args:
        user_id: ID del usuario
        grouped_context: Contexto agrupado con mensajes combinados
    """
    global adapter, conversation_manager
    
    try:
        # Verificar si debe responder basado en el patrón
        should_respond = conversation_manager.should_respond_to_pattern(
            grouped_context['conversation_pattern'],
            grouped_context['combined_message']
        )
        
        if not should_respond:
            print(f"🚫 No responder según patrón: {grouped_context['conversation_pattern']}")
            return
        
        # Procesar con el adaptador usando el mensaje combinado
        base_metadata = grouped_context['base_metadata']
        
        response = await adapter.process_whatsapp_message(
            message=grouped_context['combined_message'],
            from_jid=base_metadata['from_jid'],
            is_group=base_metadata['is_group'],
            sender_number=base_metadata['sender_number'],
            timestamp=base_metadata['timestamp'],
            message_id=base_metadata['message_id'],
            group_name=base_metadata['group_name']
        )
        
        # NUEVO: Refinar la respuesta para mejorar coherencia
        refined_response = await refine_response_with_model(
            user_message=grouped_context['combined_message'],
            original_response=response,
            user_id=user_id
        )
        print(f"🔄 Respuesta refinada para [{user_id}]")
        
        # Dividir respuesta refinada en partes humanas si es necesario
        response_parts = conversation_manager.split_response_human_like(refined_response)
        
        # Enviar cada parte con delay humano
        for i, part in enumerate(response_parts):
            await send_response_to_whatsapp(base_metadata['from_jid'], part)
            
            # Delay entre partes para simular escritura humana
            if i < len(response_parts) - 1:
                await asyncio.sleep(2)  # 2 segundos entre partes
        
    except Exception as e:
        print(f"❌ Error procesando conversación agrupada: {e}")
        # Enviar mensaje de error
        await send_response_to_whatsapp(
            grouped_context['base_metadata']['from_jid'],
            "Disculpa, tuve un problema procesando tu mensaje. ¿Podrías intentar de nuevo?"
        )

async def send_response_to_whatsapp(from_jid: str, response: str, delay: int = 0):
    """
    Agregar respuesta a la cola para que el WhatsApp Bridge la obtenga
    
    Args:
        from_jid: JID del chat de WhatsApp
        response: Mensaje de respuesta
        delay: Delay en milisegundos antes de enviar
    """
    global pending_responses
    
    response_data = {
        "jid": from_jid,
        "message": response,
        "delay": delay,
        "timestamp": datetime.now().isoformat()
    }
    
    pending_responses.append(response_data)
    
    # Log optimizado: solo salida WhatsApp
    user_id = from_jid.split('@')[0] if '@' in from_jid else from_jid
    response_preview = response[:50] + "..." if len(response) > 50 else response
    print(f"📤 WhatsApp OUT: [{user_id}] \"{response_preview}\"")

@app.get("/")
async def root():
    """Endpoint raíz de salud"""
    return {
        "service": "EconomIAssist WhatsApp Server",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "agent_ready": agent is not None
    }

@app.get("/health")
async def health_check():
    """Endpoint de verificación de salud"""
    return {
        "status": "healthy" if agent else "initializing",
        "agent_initialized": agent is not None,
        "refinement_enabled": bool(AZURE_OPENAI_API_BASE and AZURE_OPENAI_API_KEY),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/whatsapp/message")
async def handle_whatsapp_message(
    message: str = Query(..., description="Texto del mensaje de WhatsApp"),
    fromJid: str = Query(..., description="ID del chat/grupo de WhatsApp"),
    isGroup: bool = Query(False, description="Si es un mensaje de grupo"),
    senderNumber: Optional[str] = Query(None, description="Número del remitente"),
    timestamp: Optional[str] = Query(None, description="Timestamp del mensaje"),
    messageId: Optional[str] = Query(None, description="ID único del mensaje"),
    groupName: Optional[str] = Query(None, description="Nombre del grupo (si aplica)")
):
    """
    Endpoint principal que recibe mensajes del WhatsApp Bridge
    Ahora usa Conversation Manager para agrupar mensajes temporalmente
    """
    global conversation_manager
    
    if not conversation_manager:
        raise HTTPException(
            status_code=503, 
            detail="Conversation Manager no está inicializado"
        )
    
    try:
        print(f"📨 Mensaje WhatsApp recibido de {senderNumber}: {message[:50]}... [ID: {messageId}]")
        
        # Verificar si ya procesamos este mensaje (evitar duplicados)
        if messageId in processed_messages:
            print(f"⚠️ Mensaje duplicado detectado [ID: {messageId}] - Ignorando")
            return PlainTextResponse(content="", status_code=200)
        
        # Marcar mensaje como procesado
        processed_messages.add(messageId)
        print(f"✅ Mensaje marcado como procesado [ID: {messageId}]")
        
        # Limpiar cache si tiene muchas entradas (mantener últimas 1000)
        if len(processed_messages) > 1000:
            processed_messages.clear()
            print("🧹 Cache de mensajes procesados limpiado")
        
        # Preparar datos del mensaje para el Conversation Manager
        message_data = {
            'message': message,
            'from_jid': fromJid,
            'is_group': isGroup,
            'sender_number': senderNumber,
            'timestamp': timestamp,
            'message_id': messageId,
            'group_name': groupName
        }
        
        # Agregar al buffer del Conversation Manager
        user_id = senderNumber or fromJid
        buffered = await conversation_manager.add_message(user_id, message_data)
        
        if buffered:
            print(f"🕐 Mensaje agregado al buffer temporal (esperando {conversation_manager.window_seconds}s)")
            # Respuesta inmediata para el WhatsApp Bridge
            return PlainTextResponse(content="", status_code=200)
        else:
            print("⚠️ Mensaje no pudo ser agregado al buffer")
            return PlainTextResponse(content="Error interno", status_code=500)
        
    except Exception as e:
        print(f"❌ Error manejando mensaje: {e}")
        return PlainTextResponse(content="Error interno", status_code=500)

@app.get("/whatsapp/test")
async def test_endpoint():
    """Endpoint de prueba para verificar la conectividad"""
    return {
        "message": "EconomIAssist WhatsApp Server funcionando correctamente",
        "agent_status": "ready" if agent else "not_ready",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/whatsapp/pending-responses")
async def get_pending_responses():
    """
    Endpoint para que el WhatsApp Bridge obtenga respuestas pendientes
    (Silencioso - sin logs por el filtro HTTP)
    """
    global pending_responses
    
    # Obtener todas las respuestas pendientes
    responses = pending_responses.copy()
    
    # Limpiar la cola
    pending_responses.clear()
    
    return responses

async def refine_response_with_model(user_message: str, original_response: str, user_id: str) -> str:
    """
    Refina la respuesta original utilizando el mismo modelo de Azure OpenAI.
    
    Args:
        user_message: El mensaje del usuario
        original_response: La respuesta original generada por el agente
        user_id: ID del usuario para seguimiento
        
    Returns:
        str: La respuesta refinada
    """
    global azure_client
    
    # Si no hay cliente inicializado, devolver la respuesta original
    if not azure_client:
        print("⚠️ Cliente Azure OpenAI no inicializado, usando respuesta original")
        return original_response
    
    try:
        # Construir prompt para el modelo de refinamiento
        refinement_prompt = f"""
        Mensaje del usuario: {user_message}
        
        Respuesta original: {original_response}
        
        Tu tarea es revisar y refinar la respuesta anterior para que sea:
        1. Más coherente y fluida
        2. Profesional pero amigable
        3. Concisa y bien estructurada
        4. Mantener toda la información importante
        
        Solo devuelve la respuesta refinada sin explicaciones ni comentarios adicionales.
        """
        
        # Llamar directamente a la API como en el intent parser
        response = azure_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Eres un asistente de refinamiento de texto experto en economía."},
                {"role": "user", "content": refinement_prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            top_p=1.0,
            model=AZURE_OPENAI_DEPLOYMENT_NAME
        )
        
        # Extraer respuesta refinada
        refined_text = response.choices[0].message.content
        
        if not refined_text:
            print("⚠️ Respuesta vacía del modelo de refinamiento")
            return original_response
        
        return refined_text
    
    except Exception as e:
        print(f"❌ Error refinando respuesta: {e}")
        # En caso de error, devolver la respuesta original
        return original_response

if __name__ == "__main__":
    # Ejecutar el servidor
    print("🤖 EconomIAssist WhatsApp Server")
    print("=" * 50)
    
    # Configurar logging para ser menos verboso
    import logging
    logging.getLogger("uvicorn.access").addFilter(HttpPollingFilter())
    
    uvicorn.run(
        "whatsapp_server:app",
        host=WHATSAPP_SERVER_HOST,
        port=WHATSAPP_SERVER_PORT,
        reload=False,
        log_level="info"
    )