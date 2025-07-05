"""
Módulo WhatsApp para EconomIAssist
Proporciona integración con WhatsApp a través de Baileys Bridge
"""

from .whatsapp_server import app
from .message_adapter import WhatsAppMessageAdapter

__all__ = ['app', 'WhatsAppMessageAdapter']