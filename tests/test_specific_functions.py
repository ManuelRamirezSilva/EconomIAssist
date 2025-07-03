#!/usr/bin/env python3
"""
Tests específicos para diferentes funcionalidades de EconomIAssist
"""

import requests
import time
import json
from datetime import datetime
import uuid

class EconomIAssistTester:
    def __init__(self, server_url="http://localhost:8000"):
        self.server_url = server_url
        self.user_id = f"test_user_{int(time.time())}"
        
    def send_test_message(self, message, test_name=""):
        """Enviar mensaje y obtener respuesta"""
        params = {
            "message": message,
            "fromJid": f"{self.user_id}@s.whatsapp.net",
            "isGroup": False,
            "senderNumber": self.user_id,
            "timestamp": datetime.now().isoformat(),
            "messageId": str(uuid.uuid4())
        }
        
        print(f"\n{'='*60}")
        print(f"🧪 TEST: {test_name}")
        print(f"📨 Mensaje: {message}")
        print(f"{'='*60}")
        
        try:
            # Enviar mensaje
            response = requests.get(f"{self.server_url}/whatsapp/message", params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Error enviando mensaje: {response.status_code}")
                return None
            
            # Recolectar respuestas múltiples veces para capturar todas las partes
            all_responses = []
            max_attempts = 5  # Intentar 5 veces
            
            for attempt in range(max_attempts):
                print(f"⏱️ Esperando respuestas (intento {attempt + 1}/{max_attempts})...")
                time.sleep(3)  # Esperar 3 segundos entre intentos
                
                response = requests.get(f"{self.server_url}/whatsapp/pending-responses", timeout=5)
                if response.status_code == 200:
                    responses = response.json()
                    if responses:
                        all_responses.extend(responses)
                        print(f"📨 Recibidas {len(responses)} respuestas nuevas")
                    elif attempt > 2:  # Si no hay respuestas después de 3 intentos, salir
                        break
                else:
                    print(f"❌ Error obteniendo respuestas: {response.status_code}")
                    break
            
            # Mostrar todas las respuestas recolectadas
            if all_responses:
                print(f"\n🤖 Respuesta completa ({len(all_responses)} partes):")
                for i, resp in enumerate(all_responses, 1):
                    message_text = resp.get('message', '')
                    if len(all_responses) > 1:
                        print(f"[Parte {i}] {message_text}")
                    else:
                        print(f"🤖 Respuesta: {message_text}")
                return all_responses
            else:
                print("⚠️ No se recibió respuesta")
                return []
                
        except Exception as e:
            print(f"❌ Error en test: {e}")
            return None
    
    def test_basic_greeting(self):
        """Test de saludo básico"""
        return self.send_test_message("Hola", "Saludo Básico")
    
    def test_informal_greeting(self):
        """Test de saludo informal argentino"""
        return self.send_test_message("hola pa! como estas?", "Saludo Informal")
    
    def test_greeting_variations(self):
        """Test de variaciones de saludos"""
        greetings = [
            ("Hola", "Saludo Simple"),
            ("Buenos días", "Saludo Formal"),
            ("Che, ¿cómo andás?", "Saludo Argentino"),
            ("¡Buenas!", "Saludo Casual")
        ]
        
        results = []
        for greeting, test_name in greetings:
            print(f"\n{'='*40}")
            print(f"🧪 TEST SALUDO: {test_name}")
            print(f"{'='*40}")
            result = self.send_test_message(greeting, test_name)
            results.append(result)
            time.sleep(1)  # Pausa corta entre saludos
        
        return results
    
    def test_economic_question(self):
        """Test de pregunta económica"""
        return self.send_test_message(
            "¿Qué es la inflación y cómo me afecta?", 
            "Pregunta Económica"
        )
    
    def test_bcra_query(self):
        """Test de consulta al BCRA"""
        return self.send_test_message(
            "¿Cuál es la tasa de interés actual del BCRA?", 
            "Consulta BCRA"
        )
    
    def test_tax_question(self):
        """Test de pregunta sobre impuestos"""
        return self.send_test_message(
            "¿Cómo calculo el impuesto a las ganancias?", 
            "Consulta Impuestos"
        )
    
    def test_investment_advice(self):
        """Test de consejo de inversión"""
        return self.send_test_message(
            "¿Dónde puedo invertir mi dinero en Argentina?", 
            "Consejo de Inversión"
        )
    
    def test_complex_query(self):
        """Test de consulta compleja"""
        return self.send_test_message(
            "Tengo $100.000 y quiero invertir. ¿Qué opciones tengo considerando la inflación actual?", 
            "Consulta Compleja"
        )
    
    def test_informal_language(self):
        """Test con lenguaje informal argentino"""
        return self.send_test_message(
            "Che, ¿qué onda con el dólar blue? ¿Conviene comprar?", 
            "Lenguaje Informal"
        )
    
    def test_help_request(self):
        """Test de solicitud de ayuda"""
        return self.send_test_message(
            "No entiendo nada de economía, ¿me podés ayudar?", 
            "Solicitud de Ayuda"
        )
    
    def run_all_tests(self):
        """Ejecutar todos los tests"""
        print("🤖 EJECUTANDO SUITE DE TESTS PARA ECONOMIASSIST")
        print("=" * 80)
        
        tests = [
            self.test_basic_greeting,
            self.test_informal_greeting,
            self.test_greeting_variations,
            self.test_economic_question,
            self.test_bcra_query,
            self.test_tax_question,
            self.test_investment_advice,
            self.test_complex_query,
            self.test_informal_language,
            self.test_help_request
        ]
        
        results = []
        for test in tests:
            result = test()
            results.append(result)
            time.sleep(2)  # Pausa entre tests
        
        # Resumen
        print("\n" + "="*80)
        print("📊 RESUMEN DE TESTS")
        print("="*80)
        
        successful = sum(1 for r in results if r and len(r) > 0)
        total = len(results)
        
        print(f"✅ Tests exitosos: {successful}/{total}")
        print(f"❌ Tests fallidos: {total - successful}/{total}")
        
        if successful == total:
            print("🎉 ¡Todos los tests pasaron!")
        else:
            print("⚠️ Algunos tests fallaron - revisa la configuración")

def main():
    import sys
    
    tester = EconomIAssistTester()
    
    # Verificar servidor
    try:
        response = requests.get(f"{tester.server_url}/health", timeout=5)
        if response.status_code != 200 or not response.json().get("agent_initialized", False):
            print("❌ Servidor no disponible o agente no inicializado")
            print("💡 Ejecuta: python src/whatsapp/whatsapp_server.py")
            return
    except:
        print("❌ No se puede conectar al servidor")
        return
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        
        test_methods = {
            "greeting": tester.test_basic_greeting,
            "informal-greeting": tester.test_informal_greeting,
            "greeting-variations": tester.test_greeting_variations,
            "economic": tester.test_economic_question,
            "bcra": tester.test_bcra_query,
            "tax": tester.test_tax_question,
            "investment": tester.test_investment_advice,
            "complex": tester.test_complex_query,
            "informal-lang": tester.test_informal_language,
            "help": tester.test_help_request,
            "all": tester.run_all_tests
        }
        
        if test_name in test_methods:
            test_methods[test_name]()
        else:
            print(f"Tests disponibles: {', '.join(test_methods.keys())}")
    else:
        tester.run_all_tests()

if __name__ == "__main__":
    main()
