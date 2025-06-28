#!/usr/bin/env python3
"""
Servidor HTTP para recibir mensajes de WhatsApp Bridge
Integra con el ConversationalAgent existente de EconomIAssist + Conversation Manager
"""

import asyncio
import os
import sys
from typing import Optional, List, Dict
from datetime import datetime

# Agregar el directorio raíz al path para importaciones
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
import uvicorn
from dotenv import load_dotenv

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
pending_responses: List[Dict] = []  # Cola de respuestas para el WhatsApp Bridge

@app.on_event("startup")
async def startup_event():
    """Inicializar el agente conversacional y conversation manager al arrancar el servidor"""
    global agent, adapter, conversation_manager
    
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
        
        print("✅ EconomIAssist WhatsApp Server v2.0 iniciado exitosamente")
        print(f"📡 Escuchando en: http://{WHATSAPP_SERVER_HOST}:{WHATSAPP_SERVER_PORT}")
        print("🔗 Endpoint WhatsApp: /whatsapp/message")
        print("🧠 Conversation Manager: Activado (ventana: 5s)")
        
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
        print(f"🧠 Procesando conversación agrupada de {user_id}")
        print(f"   📊 Mensajes: {grouped_context['message_count']}")
        print(f"   🎭 Patrón: {grouped_context['conversation_pattern']}")
        print(f"   📝 Texto: {grouped_context['combined_message'][:50]}...")
        
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
        
        # Dividir respuesta en partes humanas si es necesario
        response_parts = conversation_manager.split_response_human_like(response)
        
        print(f"✅ Respuesta generada: {len(response_parts)} parte(s)")
        
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
    print(f"📤 Respuesta agregada a cola pendiente para {from_jid}: {response[:50]}...")

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
        print(f"📨 Mensaje WhatsApp recibido de {senderNumber}: {message[:50]}...")
        
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
    """
    global pending_responses
    
    # Obtener todas las respuestas pendientes
    responses = pending_responses.copy()
    
    # Limpiar la cola
    pending_responses.clear()
    
    return responses

if __name__ == "__main__":
    # Ejecutar el servidor
    print("🤖 EconomIAssist WhatsApp Server")
    print("=" * 50)
    
    uvicorn.run(
        "whatsapp_server:app",
        host=WHATSAPP_SERVER_HOST,
        port=WHATSAPP_SERVER_PORT,
        reload=False,
        log_level="info"
    )