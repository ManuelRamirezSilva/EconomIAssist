#!/usr/bin/env python3
"""
Test simple para el agente de WhatsApp usando requests síncronos
Script más liviano para testing rápido sin dependencias async
"""

import requests
import time
import json
import uuid
from datetime import datetime
import sys

# Colores para terminal
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

class SimpleWhatsAppTester:
    """Tester simple para mensajes de WhatsApp"""
    
    def __init__(self, server_url="http://localhost:8000"):
        self.server_url = server_url
        self.user_id = f"test_user_{int(time.time())}"
        self.from_jid = f"{self.user_id}@s.whatsapp.net"
    
    def check_server(self):
        """Verificar si el servidor está funcionando"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("agent_initialized", False)
            return False
        except Exception as e:
            print(f"{Colors.RED}❌ Error conectando: {e}{Colors.END}")
            return False
    
    def send_message(self, message, sender_number=None):
        """Enviar mensaje al servidor"""
        if not sender_number:
            sender_number = self.user_id
        
        params = {
            "message": message,
            "fromJid": self.from_jid,
            "isGroup": False,
            "senderNumber": sender_number,
            "timestamp": datetime.now().isoformat(),
            "messageId": str(uuid.uuid4())
        }
        
        try:
            print(f"{Colors.BLUE}📨 Enviando: \"{message}\"{Colors.END}")
            response = requests.get(f"{self.server_url}/whatsapp/message", params=params, timeout=10)
            
            if response.status_code == 200:
                print(f"{Colors.GREEN}✅ Mensaje enviado{Colors.END}")
                return True
            else:
                print(f"{Colors.RED}❌ Error: {response.status_code}{Colors.END}")
                return False
        except Exception as e:
            print(f"{Colors.RED}❌ Error enviando: {e}{Colors.END}")
            return False
    
    def get_responses(self):
        """Obtener respuestas del servidor"""
        try:
            response = requests.get(f"{self.server_url}/whatsapp/pending-responses", timeout=5)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Error obteniendo respuestas: {e}{Colors.END}")
            return []
    
    def test_single_message(self, message):
        """Testear un solo mensaje"""
        print(f"\n{Colors.BOLD}=== Test de mensaje único ==={Colors.END}")
        
        success = self.send_message(message)
        if not success:
            return
        
        # Recolectar respuestas múltiples veces para capturar todas las partes
        all_responses = []
        max_attempts = 6  # Intentar 6 veces
        
        for attempt in range(max_attempts):
            print(f"{Colors.YELLOW}⏱️ Esperando respuestas (intento {attempt + 1}/{max_attempts})...{Colors.END}")
            time.sleep(3)  # Esperar 3 segundos entre intentos
            
            responses = self.get_responses()
            if responses:
                all_responses.extend(responses)
                print(f"{Colors.BLUE}📨 Recibidas {len(responses)} respuestas nuevas{Colors.END}")
            else:
                print(f"{Colors.YELLOW}⚠️ Sin respuestas en este intento{Colors.END}")
        
        # Mostrar todas las respuestas recolectadas
        if all_responses:
            print(f"\n{Colors.BOLD}🤖 Respuesta completa ({len(all_responses)} partes):{Colors.END}")
            for i, response in enumerate(all_responses, 1):
                message_text = response.get('message', '')
                print(f"{Colors.GREEN}[Parte {i}] {message_text}{Colors.END}")
        else:
            print(f"{Colors.YELLOW}⚠️ No se recibió respuesta completa{Colors.END}")
    
    def test_conversation(self):
        """Testear una conversación completa"""
        messages = [
            "Hola",
            "¿Qué es la inflación?",
            "¿Cómo me afecta?",
            "Gracias"
        ]
        
        print(f"\n{Colors.BOLD}=== Test de conversación ==={Colors.END}")
        print(f"Usuario: {self.user_id}")
        
        for i, message in enumerate(messages, 1):
            print(f"\n{Colors.BOLD}[{i}/{len(messages)}]{Colors.END}")
            
            success = self.send_message(message)
            if not success:
                continue
            
            # Recolectar respuestas múltiples
            all_responses = []
            max_attempts = 4
            
            for attempt in range(max_attempts):
                print(f"{Colors.YELLOW}⏱️ Esperando ({attempt + 1}/{max_attempts})...{Colors.END}")
                time.sleep(3)
                
                responses = self.get_responses()
                if responses:
                    all_responses.extend(responses)
                elif attempt > 1:  # Si no hay respuestas después de 2 intentos, salir
                    break
            
            # Mostrar respuestas
            if all_responses:
                for response in all_responses:
                    print(f"{Colors.GREEN}🤖 {response.get('message', '')}{Colors.END}")
            else:
                print(f"{Colors.YELLOW}⚠️ Sin respuesta{Colors.END}")
            
            # Pausa entre mensajes
            if i < len(messages):
                time.sleep(2)
    
    def interactive_mode(self):
        """Modo interactivo"""
        print(f"\n{Colors.BOLD}=== Modo Interactivo ==={Colors.END}")
        print(f"{Colors.BLUE}Escribe 'quit' para salir{Colors.END}")
        
        while True:
            try:
                message = input(f"\n{Colors.BOLD}💬 Tu mensaje: {Colors.END}")
                
                if message.lower() in ['quit', 'exit', 'salir']:
                    print(f"{Colors.GREEN}👋 ¡Hasta luego!{Colors.END}")
                    break
                
                if not message.strip():
                    continue
                
                success = self.send_message(message)
                if not success:
                    continue
                
                # Recolectar respuestas múltiples para capturar todas las partes
                all_responses = []
                max_attempts = 4
                
                for attempt in range(max_attempts):
                    print(f"{Colors.YELLOW}⏱️ Esperando respuestas ({attempt + 1}/{max_attempts})...{Colors.END}")
                    time.sleep(3)
                    
                    responses = self.get_responses()
                    if responses:
                        all_responses.extend(responses)
                        if attempt == 0:  # Primera respuesta
                            print(f"{Colors.BLUE}📨 Recibiendo respuesta...{Colors.END}")
                    
                    # Si no hay más respuestas después de 2 intentos sin nada, salir
                    if attempt > 1 and not responses:
                        break
                
                # Mostrar respuestas
                if all_responses:
                    for i, response in enumerate(all_responses, 1):
                        message_text = response.get('message', '')
                        if len(all_responses) > 1:
                            print(f"{Colors.GREEN}🤖 EconomIAssist [Parte {i}]: {message_text}{Colors.END}")
                        else:
                            print(f"{Colors.GREEN}🤖 EconomIAssist: {message_text}{Colors.END}")
                else:
                    print(f"{Colors.YELLOW}⚠️ No se recibió respuesta{Colors.END}")
                    
            except KeyboardInterrupt:
                print(f"\n{Colors.GREEN}👋 ¡Hasta luego!{Colors.END}")
                break

def main():
    """Función principal"""
    print(f"{Colors.BOLD}🤖 Test Simple para EconomIAssist WhatsApp{Colors.END}")
    print("=" * 50)
    
    tester = SimpleWhatsAppTester()
    
    # Verificar servidor
    print(f"{Colors.BLUE}🔍 Verificando servidor...{Colors.END}")
    if not tester.check_server():
        print(f"{Colors.RED}❌ Servidor no disponible{Colors.END}")
        print(f"{Colors.YELLOW}💡 Ejecuta: python src/whatsapp/whatsapp_server.py{Colors.END}")
        return
    
    print(f"{Colors.GREEN}✅ Servidor OK{Colors.END}")
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "test":
            tester.test_conversation()
        elif mode == "single" and len(sys.argv) > 2:
            message = " ".join(sys.argv[2:])
            tester.test_single_message(message)
        else:
            print(f"{Colors.YELLOW}Uso: python simple_whatsapp_test.py [test|single|interactive] [mensaje]{Colors.END}")
            tester.interactive_mode()
    else:
        tester.interactive_mode()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.GREEN}👋 Programa interrumpido{Colors.END}")
