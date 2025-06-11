#!/usr/bin/env python3
"""
Servidor HTTP para recibir mensajes de WhatsApp Bridge
Integra con el ConversationalAgent existente de EconomIAssist
"""

import asyncio
import os
import sys
from typing import Optional
from datetime import datetime

# Agregar el directorio raíz al path para importaciones
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
import uvicorn
from dotenv import load_dotenv

# Importar el agente conversacional existente
from src.agent.conversational_agent import ConversationalAgent
from src.whatsapp.message_adapter import WhatsAppMessageAdapter

# Cargar variables de entorno
load_dotenv()

# Configuración
WHATSAPP_SERVER_HOST = os.getenv("WHATSAPP_SERVER_HOST", "localhost")
WHATSAPP_SERVER_PORT = int(os.getenv("WHATSAPP_SERVER_PORT", "8000"))

# Crear instancia de FastAPI
app = FastAPI(
    title="EconomIAssist WhatsApp Server",
    description="Servidor HTTP que recibe mensajes de WhatsApp Bridge y los procesa con EconomIAssist",
    version="1.0.0"
)

# Variables globales
agent: Optional[ConversationalAgent] = None
adapter: Optional[WhatsAppMessageAdapter] = None

@app.on_event("startup")
async def startup_event():
    """Inicializar el agente conversacional al arrancar el servidor"""
    global agent, adapter
    
    print("🚀 Iniciando EconomIAssist WhatsApp Server...")
    
    try:
        # Inicializar el agente conversacional
        agent = ConversationalAgent()
        initialized = await agent.initialize()
        
        if not initialized:
            raise Exception("No se pudo inicializar el agente conversacional")
        
        # Inicializar el adaptador de mensajes
        adapter = WhatsAppMessageAdapter(agent)
        
        print("✅ EconomIAssist WhatsApp Server iniciado exitosamente")
        print(f"📡 Escuchando en: http://{WHATSAPP_SERVER_HOST}:{WHATSAPP_SERVER_PORT}")
        print("🔗 Endpoint WhatsApp: /whatsapp/message")
        
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
    Procesa el mensaje con EconomIAssist y devuelve la respuesta
    """
    global agent, adapter
    
    if not agent or not adapter:
        raise HTTPException(
            status_code=503, 
            detail="EconomIAssist no está inicializado correctamente"
        )
    
    try:
        print(f"📨 Mensaje WhatsApp recibido de {senderNumber}: {message[:50]}...")
        
        # Usar el adaptador para procesar el mensaje
        response = await adapter.process_whatsapp_message(
            message=message,
            from_jid=fromJid,
            is_group=isGroup,
            sender_number=senderNumber,
            timestamp=timestamp,
            message_id=messageId,
            group_name=groupName
        )
        
        print(f"✅ Respuesta generada: {len(response)} caracteres")
        
        # Devolver respuesta como texto plano (más compatible con WhatsApp Bridge)
        return PlainTextResponse(content=response)
        
    except Exception as e:
        print(f"❌ Error procesando mensaje: {e}")
        
        # Devolver error amigable al usuario
        error_response = "Lo siento, hubo un problema procesando tu mensaje. Intenta de nuevo en unos momentos."
        return PlainTextResponse(content=error_response, status_code=500)

@app.get("/whatsapp/test")
async def test_endpoint():
    """Endpoint de prueba para verificar la conectividad"""
    return {
        "message": "EconomIAssist WhatsApp Server funcionando correctamente",
        "agent_status": "ready" if agent else "not_ready",
        "timestamp": datetime.now().isoformat()
    }

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