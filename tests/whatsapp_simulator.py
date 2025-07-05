#!/usr/bin/env python3
"""
Simulador de mensajes de WhatsApp para testear EconomIAssist
Permite enviar mensajes de prueba al servidor como si vinieran de WhatsApp
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Optional, List, Dict
import uuid
import argparse
import sys
import os

# Colores para la terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class WhatsAppSimulator:
    """Simulador de mensajes de WhatsApp para testing"""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.session = None
        self.user_id = "test_user_" + str(int(time.time()))
        self.from_jid = f"{self.user_id}@s.whatsapp.net"
        
    async def __aenter__(self):
        """Inicializar session HTTP"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cerrar session HTTP"""
        if self.session:
            await self.session.close()
    
    async def check_server_health(self) -> bool:
        """Verificar si el servidor está funcionando"""
        try:
            async with self.session.get(f"{self.server_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("agent_initialized", False)
                return False
        except Exception as e:
            print(f"{Colors.FAIL}❌ Error conectando al servidor: {e}{Colors.ENDC}")
            return False
    
    async def send_message(
        self,
        message: str,
        sender_number: str = None,
        is_group: bool = False,
        group_name: str = None
    ) -> bool:
        """
        Enviar un mensaje simulado al servidor de WhatsApp
        
        Args:
            message: Texto del mensaje
            sender_number: Número del remitente (opcional)
            is_group: Si es mensaje de grupo
            group_name: Nombre del grupo (si aplica)
            
        Returns:
            bool: True si el mensaje se envió correctamente
        """
        if not sender_number:
            sender_number = self.user_id
        
        # Generar ID único para el mensaje
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Parámetros para el endpoint
        params = {
            "message": message,
            "fromJid": self.from_jid,
            "isGroup": is_group,
            "senderNumber": sender_number,
            "timestamp": timestamp,
            "messageId": message_id
        }
        
        if group_name:
            params["groupName"] = group_name
        
        try:
            print(f"{Colors.OKBLUE}📨 Enviando: \"{message}\"{Colors.ENDC}")
            
            async with self.session.get(
                f"{self.server_url}/whatsapp/message",
                params=params
            ) as response:
                
                if response.status == 200:
                    print(f"{Colors.OKGREEN}✅ Mensaje enviado correctamente{Colors.ENDC}")
                    return True
                else:
                    print(f"{Colors.FAIL}❌ Error enviando mensaje: {response.status}{Colors.ENDC}")
                    return False
                    
        except Exception as e:
            print(f"{Colors.FAIL}❌ Error enviando mensaje: {e}{Colors.ENDC}")
            return False
    
    async def get_responses(self) -> List[Dict]:
        """Obtener respuestas pendientes del servidor"""
        try:
            async with self.session.get(f"{self.server_url}/whatsapp/pending-responses") as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            print(f"{Colors.WARNING}⚠️ Error obteniendo respuestas: {e}{Colors.ENDC}")
            return []
    
    async def simulate_conversation(self, messages: List[str], delay: float = 2.0):
        """
        Simular una conversación completa
        
        Args:
            messages: Lista de mensajes a enviar
            delay: Tiempo entre mensajes en segundos
        """
        print(f"{Colors.HEADER}🤖 Iniciando simulación de conversación{Colors.ENDC}")
        print(f"{Colors.HEADER}Usuario simulado: {self.user_id}{Colors.ENDC}")
        print("=" * 60)
        
        for i, message in enumerate(messages, 1):
            print(f"\n{Colors.BOLD}[Mensaje {i}/{len(messages)}]{Colors.ENDC}")
            
            # Enviar mensaje
            success = await self.send_message(message)
            if not success:
                continue
            
            # Esperar un poco para que el servidor procese
            await asyncio.sleep(1)
            
            # Obtener respuestas
            responses = await self.get_responses()
            
            # Mostrar respuestas
            if responses:
                for response in responses:
                    print(f"{Colors.OKCYAN}🤖 Respuesta: \"{response.get('message', '')}\"{Colors.ENDC}")
            else:
                print(f"{Colors.WARNING}⚠️ No se recibió respuesta{Colors.ENDC}")
            
            # Delay entre mensajes (excepto el último)
            if i < len(messages):
                print(f"{Colors.WARNING}⏱️ Esperando {delay}s...{Colors.ENDC}")
                await asyncio.sleep(delay)
        
        print(f"\n{Colors.HEADER}✅ Simulación completada{Colors.ENDC}")

async def interactive_mode(simulator: WhatsAppSimulator):
    """Modo interactivo para enviar mensajes manualmente"""
    print(f"{Colors.HEADER}🔄 Modo interactivo activado{Colors.ENDC}")
    print(f"{Colors.OKCYAN}Escribe 'quit' para salir{Colors.ENDC}")
    print("=" * 60)
    
    while True:
        try:
            # Solicitar input del usuario
            message = input(f"\n{Colors.BOLD}💬 Tu mensaje: {Colors.ENDC}")
            
            if message.lower() in ['quit', 'exit', 'salir']:
                print(f"{Colors.HEADER}👋 ¡Hasta luego!{Colors.ENDC}")
                break
            
            if not message.strip():
                continue
            
            # Enviar mensaje
            success = await simulator.send_message(message)
            if not success:
                continue
            
            # Esperar un poco para respuesta
            print(f"{Colors.WARNING}⏱️ Esperando respuesta...{Colors.ENDC}")
            await asyncio.sleep(2)
            
            # Obtener y mostrar respuestas
            responses = await simulator.get_responses()
            
            if responses:
                for response in responses:
                    print(f"{Colors.OKCYAN}🤖 EconomIAssist: \"{response.get('message', '')}\"{Colors.ENDC}")
            else:
                print(f"{Colors.WARNING}⚠️ No se recibió respuesta{Colors.ENDC}")
                
        except KeyboardInterrupt:
            print(f"\n{Colors.HEADER}👋 ¡Hasta luego!{Colors.ENDC}")
            break
        except Exception as e:
            print(f"{Colors.FAIL}❌ Error: {e}{Colors.ENDC}")

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Simulador de WhatsApp para EconomIAssist")
    parser.add_argument(
        "--server", 
        default="http://localhost:8000",
        help="URL del servidor de WhatsApp (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Modo interactivo para enviar mensajes manualmente"
    )
    parser.add_argument(
        "--test-conversation",
        action="store_true",
        help="Ejecutar conversación de prueba predefinida"
    )
    
    args = parser.parse_args()
    
    print(f"{Colors.HEADER}🤖 WhatsApp Simulator para EconomIAssist{Colors.ENDC}")
    print(f"{Colors.HEADER}Servidor: {args.server}{Colors.ENDC}")
    print("=" * 60)
    
    async with WhatsAppSimulator(args.server) as simulator:
        # Verificar salud del servidor
        print(f"{Colors.OKBLUE}🔍 Verificando servidor...{Colors.ENDC}")
        is_healthy = await simulator.check_server_health()
        
        if not is_healthy:
            print(f"{Colors.FAIL}❌ El servidor no está disponible o el agente no está inicializado{Colors.ENDC}")
            print(f"{Colors.WARNING}💡 Asegúrate de que el servidor esté corriendo con: python src/whatsapp/whatsapp_server.py{Colors.ENDC}")
            return
        
        print(f"{Colors.OKGREEN}✅ Servidor funcionando correctamente{Colors.ENDC}")
        
        if args.interactive:
            await interactive_mode(simulator)
        elif args.test_conversation:
            # Conversación de prueba predefinida
            test_messages = [
                "Hola",
                "¿Qué es la inflación?",
                "¿Cómo afecta la inflación a mi economía personal?",
                "¿Qué medidas puedo tomar para protegerme de la inflación?",
                "Gracias por la información"
            ]
            await simulator.simulate_conversation(test_messages, delay=3.0)
        else:
            # Por defecto, modo interactivo
            await interactive_mode(simulator)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.HEADER}👋 ¡Programa interrumpido!{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}❌ Error fatal: {e}{Colors.ENDC}")
        sys.exit(1)
