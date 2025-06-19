import os  # Keep this import at the top
import sys
from openai import AzureOpenAI
from dotenv import load_dotenv
import pydantic
import json
import time
import structlog  # Add this import


class IntentResponse(pydantic.BaseModel):
    intent: str
    value: str

class MultiIntentResponse(pydantic.BaseModel):
    intents: list[IntentResponse]

class IntentParser:
    def __init__(self):
        # Carga variables de entorno desde .env
        load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
        # Leer credenciales Azure OpenAI desde .env
        self.endpoint = os.getenv("AZURE_OPENAI_API_BASE")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        # Verificar credenciales
        if not all([self.endpoint, self.api_key, self.api_version, self.deployment]):
            raise ValueError("Faltan credenciales de Azure OpenAI en el archivo .env")
        
        # Create the OpenAI client
        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version
        )
        
        # Initialize intent logger
        try:
            from ..utils.intent_logger import IntentLogger
            self.intent_logger = IntentLogger(parser_id="main_intent_parser")
        except ImportError:
            # Remove the os import here since it's already imported at the top level
            sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
            from utils.intent_logger import IntentLogger
            self.intent_logger = IntentLogger(parser_id="main_intent_parser")
    
        # Set a reference to the logger for use throughout the class
        self.logger = self.intent_logger
    
        self.intent_logger.info("Intent parser instance created")
        
        # Log initialization
        azure_config = {
            "api_base": self.endpoint,
            "api_version": self.api_version,
            "deployment": self.deployment,
            "api_key": "[REDACTED]"  # Redacted for security
        }
        
        self.intent_logger.log_parser_initialization(
            success=True, 
            azure_config=azure_config
        )

        self.count_intents_prompt = (
            "Eres un experto en analizar mensajes de usuarios para EconomIAssist, un asistente financiero integral con capacidades MCP avanzadas. "
            "Tu trabajo es contar cuántas intenciones distintas (acciones o solicitudes) están presentes en el mensaje del usuario. "
            
            "EconomIAssist integra los siguientes servidores MCP con capacidades específicas:\n"
            "🏦 Búsqueda Web Financiera: Datos económicos argentinos (dólar, inflación, tasas, MERVAL, análisis)\n"
            "🌐 Tavily Server: Búsqueda web inteligente y noticias financieras\n"
            "💾 Knowledge Base: Memoria conversacional y registros personales\n"
            "🧮 Calculator: Cálculos matemáticos y financieros precisos\n"
            "📅 Google Calendar: Gestión de agenda y eventos\n"
            "📊 Google Sheets: Hojas de cálculo y gestión documental\n"
            
            "Capacidades que pueden generar intenciones múltiples:\n"
            "- Consultas económicas combinadas (dólar + inflación + análisis)\n"
            "- Gestión de registros financieros (anotar + calcular + programar)\n"
            "- Análisis e investigación (buscar + analizar + recordar)\n"
            "- Planificación financiera (calcular + agendar + documentar)\n"
            "- Seguimiento de inversiones y portfolio\n"
            "- Educación y asesoramiento personalizado\n"
            
            "Reconoce jerga argentina: 'palos verdes' (millones USD), 'lucas' (miles pesos), 'blue/oficial/MEP/CCL' (dólares)\n"
            
            "Cuenta cada solicitud o acción distinta que el usuario quiere realizar. "
            "Devuelve SOLO el número como un entero. No incluyas ninguna explicación o texto adicional.\n"
            
            "Ejemplos con capacidades MCP reales:\n"
            "Usuario: 'Cuánto está el blue y agendame recordatorio para revisar mis inversiones mañana'\n"
            "Salida: 2\n"
            "Usuario: 'Dame la inflación actual, calcula el impacto en mi presupuesto de 500 lucas y búscame noticias al respecto'\n"
            "Salida: 3\n"
            "Usuario: 'Quiero un análisis económico completo con recomendaciones'\n"
            "Salida: 1\n"
            "Usuario: 'Anota que gasté 200 mil en supermercado, calcula cuánto me queda del presupuesto mensual y compárteme la planilla'\n"
            "Salida: 3\n"
            "Usuario: 'A cuánto está el dólar oficial hoy?'\n"
            "Salida: 1\n"
            "Usuario: 'Busca noticias sobre las nuevas medidas del BCRA y programa una reunión para analizarlas'\n"
            "Salida: 2\n"
            "Usuario: 'No gasté nada ayer, fue un error en mi registro'\n"
            "Salida: 1\n"
            "IMPORTANTE: Tu ÚNICA tarea es contar el número de intenciones. NO respondas a las consultas del usuario ni ofrezcas explicaciones. "
            "Devuelve SOLO el número como un entero. No incluyas ninguna explicación o texto adicional.\n"
        )

        self.system_prompt = (
            "Eres un experto analizador de intenciones para EconomIAssist, un asistente financiero integral especializado en el contexto económico argentino.\n"
            
            "🏦 SISTEMA MCP INTEGRADO - CAPACIDADES COMPLETAS:\n"
            
            "📈 1. BÚSQUEDA WEB FINANCIERA (Datos Económicos Argentinos):\n"
            "Herramientas disponibles:\n"
            "   • get_dollar_rates: Cotizaciones USD (oficial, blue, MEP, CCL)\n"
            "   • get_inflation_data: Inflación mensual, anual e interanual oficial\n"
            "   • get_interest_rates: Tasas BADLAR, LELIQ, Plazo Fijo\n"
            "   • get_reserves_data: Reservas internacionales actuales e históricas\n"
            "   • get_market_data: MERVAL, riesgo país, bonos\n"
            "   • get_economic_analysis: Análisis integral con insights y recomendaciones\n"
            "Funcionalidades: Búsqueda web de información financiera, procesamiento de datos económicos actuales\n"
            "Fuente: Búsqueda web en tiempo real con Tavily\n"
            
            "🌐 2. SERVIDOR TAVILY (Búsqueda Web Inteligente):\n"
            "Herramientas disponibles:\n"
            "   • search: Búsqueda web general con IA\n"
            "   • news_search: Noticias específicas en tiempo real\n"
            "Funcionalidades: Noticias financieras, información económica actual,\n"
            "investigación de inversiones, análisis de mercados globales,\n"
            "contenido educativo financiero, datos en tiempo real\n"
            
            "💾 3. SERVIDOR KNOWLEDGE BASE (Memoria Conversacional):\n"
            "Funcionalidades: Docker container con SQLite persistente\n"
            "   • Retención de preferencias del usuario\n"
            "   • Historial de transacciones y consultas\n"
            "   • Contexto conversacional continuo\n"
            "   • Personalización de respuestas financieras\n"
            "   • Registros contables y financieros\n"
            "   • Búsqueda semántica en historial\n"
            
            "🧮 4. SERVIDOR CALCULATOR (Cálculos Matemáticos):\n"
            "Funcionalidades: Cálculos precisos y confiables\n"
            "   • Operaciones aritméticas complejas\n"
            "   • Evaluación de expresiones matemáticas\n"
            "   • Cálculos de interés compuesto y simple\n"
            "   • Conversiones de moneda y unidades\n"
            "   • Cálculos de presupuesto y finanzas personales\n"
            "   • Análisis de ROI y rentabilidad\n"
            
            "📅 5. SERVIDOR GOOGLE CALENDAR (Gestión de Agenda):\n"
            "Herramientas disponibles:\n"
            "   • create_event: Crear eventos con detalles completos\n"
            "   • list_events: Listar eventos por rango de fechas\n"
            "   • update_event: Modificar eventos existentes\n"
            "   • delete_event: Eliminar eventos\n"
            "   • check_availability: Verificar disponibilidad horaria\n"
            "Funcionalidades: Service Account OAuth, zona horaria Argentina,\n"
            "recordatorios financieros, reuniones de planificación\n"
            
            "📊 6. SERVIDOR GOOGLE SHEETS (Hojas de Cálculo Financieras):\n"
            "Herramientas disponibles:\n"
            "   • read_sheet: Leer datos de hojas específicas\n"
            "   • write_sheet: Escribir datos en rangos específicos\n"
            "   • create_sheet: Crear nuevas hojas de cálculo\n"
            "   • batch_update: Operaciones masivas en múltiples rangos\n"
            "   • share_sheet: Compartir documentos con permisos\n"
            "   • list_files: Explorar archivos en Google Drive\n"
            "Funcionalidades: Service Account, Google Drive integrado,\n"
            "gestión de presupuestos, registros contables, análisis financiero,\n"
            "creación de pestañas, lectura de fórmulas\n"
            
            "🎯 CATEGORÍAS DE INTENCIONES ACTUALIZADAS:\n"
            
            "📈 DATOS ECONÓMICOS FINANCIEROS:\n"
            "• COTIZACION_DOLAR: Cotizaciones USD (oficial/blue/MEP/CCL/brecha)\n"
            "• DATOS_INFLACION: Inflación mensual/anual actual\n"
            "• TASAS_INTERES: BADLAR, LELIQ, plazo fijo\n"
            "• RESERVAS_INTERNACIONALES: Reservas internacionales actuales/históricas\n"
            "• INDICES_MERCADO: MERVAL, riesgo país, bonos\n"
            "• ANALISIS_ECONOMICO: Análisis integral con insights\n"
            
            "🌐 BÚSQUEDA E INVESTIGACIÓN:\n"
            "• BUSCAR_NOTICIAS_FINANCIERAS: Noticias económicas en tiempo real\n"
            "• INVESTIGAR_INVERSIONES: Información sobre activos y mercados\n"
            "• BUSCAR_INFO_ECONOMICA: Datos económicos específicos web\n"
            "• INVESTIGAR_TENDENCIAS: Análisis de tendencias económicas\n"
            
            "📅 GESTIÓN DE CALENDARIO:\n"
            "• CREAR_EVENTO: Agendar reuniones, recordatorios, citas\n"
            "• CONSULTAR_AGENDA: Ver eventos, disponibilidad, horarios\n"
            "• GESTIONAR_CALENDARIO: Modificar, eliminar, actualizar eventos\n"
            "• VERIFICAR_DISPONIBILIDAD: Comprobar horarios libres\n"
            
            "📊 GESTIÓN DE HOJAS DE CÁLCULO:\n"
            "• GESTIONAR_HOJA_CALCULO: Crear/editar hojas de presupuesto\n"
            "• REGISTRAR_TRANSACCION: Anotar ingresos/gastos en planillas\n"
            "• CONSULTAR_REGISTROS: Ver datos financieros de hojas\n"
            "• COMPARTIR_DOCUMENTO: Compartir planillas financieras\n"
            "• OPERACIONES_LOTE: Actualizar múltiples rangos en hojas\n"
            "• BUSCAR_ARCHIVOS: Explorar archivos en Google Drive\n"
            
            "🧮 CÁLCULOS MATEMÁTICOS:\n"
            "• CALCULAR_MATEMATICO: Operaciones, porcentajes, conversiones\n"
            "• CALCULAR_FINANCIERO: Interés, préstamos, ROI, rentabilidad\n"
            "• EVALUAR_EXPRESION: Expresiones matemáticas complejas\n"
            "• CONVERTIR_MONEDA: Conversiones entre divisas\n"
            
            "💾 MEMORIA Y PERSONALIZACIÓN:\n"
            "• RECORDAR_PREFERENCIA: Guardar información personal\n"
            "• CONSULTAR_HISTORIAL: Revisar interacciones anteriores\n"
            "• PERSONALIZAR_RESPUESTA: Ajustar comportamiento del asistente\n"
            "• BUSCAR_MEMORIA: Búsqueda en historial conversacional\n"
            
            "❓ CONSULTAS GENERALES:\n"
            "• CONSULTA_GENERAL: Preguntas generales sin acciones específicas\n"
            "• EDUCACION_FINANCIERA: Explicaciones de conceptos financieros\n"
            "• ASESORAMIENTO: Consejos y recomendaciones financieras\n"
            
            "🇦🇷 CONTEXTO ARGENTINO ESPECÍFICO:\n"
            "Jerga y términos reconocidos:\n"
            "- 'palos verdes' = millones de dólares\n"
            "- 'lucas' = miles de pesos\n"
            "- 'blue', 'oficial', 'MEP', 'CCL' para dólares\n"
            "- 'cueva', 'arbolito', 'financiero' para cambio\n"
            "- Referencias: inflación, cepo, brecha cambiaria\n"
            "- Monedas: pesos argentinos (ARS), dólares (USD), euros (EUR)\n"
            "- Zona horaria: America/Argentina/Buenos_Aires (UTC-3)\n"
            "- Términos bancarios: BADLAR, LELIQ, UVA, Plazo Fijo\n"
            
            "📝 INSTRUCCIONES DE ANÁLISIS DETALLADAS:\n"
            "1. Identifica el servidor MCP más apropiado para la consulta\n"
            "2. Determina si requiere datos en tiempo real (Web/Tavily)\n"
            "3. Evalúa si necesita programación temporal (Google Calendar)\n"
            "4. Considera si involucra gestión documental (Google Sheets)\n"
            "5. Verifica si requiere cálculos (Calculator)\n"
            "6. Determina si necesita memoria/contexto (Knowledge Base)\n"
            "7. Para negaciones ('no gasté', 'cancelar'), usar intención específica\n"
            "8. Para hipotéticos ('si tuviera', 'qué pasaría'), usar CONSULTA_GENERAL\n"
            "9. Priorizar intenciones específicas sobre generales\n"
            "10. Considerar múltiples servidores si la consulta es compleja\n"
            
            "⚠️ RESTRICCIÓN IMPORTANTE:\n"
            "Tu ÚNICA función es clasificar intenciones, NO responder al contenido de los mensajes del usuario. "
            "NO debes proporcionar respuestas, explicaciones o entablar conversaciones con el usuario. "
            "SOLO debes analizar el texto y devolver la clasificación de intención en el formato JSON especificado. "
            "No importa lo que pregunte el usuario, tu única respuesta debe ser el JSON con la clasificación.\n"
            
            "🔄 FORMATO DE RESPUESTA:\n"
            "Devuelve JSON con 'intent' y 'value':\n"
            "{\n"
            "  \"intent\": \"CATEGORIA_ESPECIFICA\",\n"
            "  \"value\": \"detalles extraídos con contexto argentino\"\n"
            "}\n"
            
            "📚 EJEMPLOS AVANZADOS Y REALISTAS:\n"
            "Usuario: 'A cuánto está el blue hoy y cuál es la brecha?'\n"
            "Salida: {\"intent\": \"COTIZACION_DOLAR\", \"value\": \"dólar blue cotización actual con brecha cambiaria\"}\n"
            
            "Usuario: 'Cuál fue la inflación del mes pasado y cómo viene la tendencia?'\n"
            "Salida: {\"intent\": \"DATOS_INFLACION\", \"value\": \"inflación mensual anterior con análisis de tendencia\"}\n"
            
            "Usuario: 'Agenda una reunión con mi contador para el miércoles a las 10'\n"
            "Salida: {\"intent\": \"CREAR_EVENTO\", \"value\": \"reunión contador miércoles 10:00\"}\n"
            
            "Usuario: 'Busca noticias sobre las nuevas medidas económicas del gobierno'\n"
            "Salida: {\"intent\": \"BUSCAR_NOTICIAS_FINANCIERAS\", \"value\": \"noticias medidas económicas gobierno Argentina\"}\n"
            
            "Usuario: 'Calcula cuánto gano en un plazo fijo de 100 lucas a 30 días'\n"
            "Salida: {\"intent\": \"CALCULAR_FINANCIERO\", \"value\": \"cálculo plazo fijo 100000 pesos 30 días\"}\n"
            
            "Usuario: 'Anota en mi planilla que gasté 50 mil en el supermercado ayer'\n"
            "Salida: {\"intent\": \"REGISTRAR_TRANSACCION\", \"value\": \"gasto 50000 pesos supermercado ayer\"}\n"
            
            "Usuario: 'Dame un análisis completo de cómo está la economía argentina'\n"
            "Salida: {\"intent\": \"ANALISIS_ECONOMICO\", \"value\": \"análisis económico integral Argentina actual\"}\n"
            
            "Usuario: 'Recordá que mi límite mensual de gastos es 200 mil pesos'\n"
            "Salida: {\"intent\": \"RECORDAR_PREFERENCIA\", \"value\": \"límite mensual gastos 200000 pesos\"}\n"
            
            "Usuario: 'Qué inversiones me recomendás con la inflación actual?'\n"
            "Salida: {\"intent\": \"ASESORAMIENTO\", \"value\": \"recomendaciones inversión contexto inflación actual\"}\n"
            
            "Usuario: 'Compartí mi planilla de gastos con mi esposa'\n"
            "Salida: {\"intent\": \"COMPARTIR_DOCUMENTO\", \"value\": \"compartir planilla gastos esposa\"}\n"
            
            "Usuario: 'Cuándo fue la última vez que consulté el dólar?'\n"
            "Salida: {\"intent\": \"CONSULTAR_HISTORIAL\", \"value\": \"última consulta dólar en historial\"}\n"
        )

        self.split_intents_prompt = (
            "Eres un experto en analizar mensajes de usuarios para EconomIAssist, un asistente financiero argentino con capacidades MCP integrales. "
            "El mensaje del usuario puede contener múltiples intenciones relacionadas con:\n"
            "🏦 Datos económicos (Web): dólares, inflación, tasas, análisis\n"
            "🌐 Búsqueda web: noticias financieras, investigación de inversiones\n"
            "📅 Calendario: agendar reuniones, recordatorios financieros\n"
            "📊 Hojas de cálculo: registros, presupuestos, compartir documentos\n"
            "🧮 Cálculos: operaciones financieras, conversiones, intereses\n"
            "💾 Memoria: preferencias, historial, personalización\n"
            
            "Reconoce jerga argentina:\n"
            "- 'palos verdes' = millones de dólares\n"
            "- 'lucas' = miles de pesos\n"
            "- 'blue/oficial/MEP/CCL' = tipos de dólar\n"
            "- 'cueva', 'arbolito' = cambio informal\n"
            
            "IMPORTANTE: Tu ÚNICA tarea es dividir el mensaje en intenciones separadas. "
            "NO respondas a las consultas del usuario ni ofrezcas explicaciones o contenido adicional. "
            "Divide el mensaje en intenciones separadas, manteniendo el contexto argentino. "
            "Si el mensaje contiene múltiples preguntas unidas por 'o', 'y', 'además', 'también', divide cada una como intención separada. "
            "Devuelve un array JSON de strings. No expliques, solo devuelve el array.\n"
            
            "Ejemplos con contexto argentino:\n"
            "Usuario: 'Me dieron 2 palos verdes. Me conviene pasarlos a pesos o invertir en plazo fijo?'\n"
            "Salida: [\"Me dieron 2 palos verdes.\", \"Me conviene pasarlos a pesos?\", \"Me conviene invertir en plazo fijo?\"]\n"
            
            "Usuario: 'Cuánto está el blue hoy y cuál es la inflación de este mes?'\n"
            "Salida: [\"Cuánto está el blue hoy\", \"cuál es la inflación de este mes\"]\n"
            
            "Usuario: 'Anota que gasté 50 lucas en el super y programa reunión con el contador'\n"
            "Salida: [\"Anota que gasté 50 lucas en el super\", \"programa reunión con el contador\"]\n"
            
            "Usuario: 'Búscame noticias sobre el nuevo gobierno, calcula mi ROI del año y compartí mi planilla de inversiones'\n"
            "Salida: [\"Búscame noticias sobre el nuevo gobierno\", \"calcula mi ROI del año\", \"compartí mi planilla de inversiones\"]\n"
            
            "Usuario: 'Dame un análisis económico completo de Argentina'\n"
            "Salida: [\"Dame un análisis económico completo de Argentina\"]\n"
            
            "Usuario: 'Recordá que mi límite de gastos es 300 lucas y avísame cuando lo supere'\n"
            "Salida: [\"Recordá que mi límite de gastos es 300 lucas\", \"avísame cuando lo supere\"]\n"
        )

        # Set the logger as an alias to intent_logger
        self.logger = self.intent_logger
    
    def receive_message(self, message: str):
        """Procesa un mensaje del usuario y extrae las intenciones"""
        start_time = time.time()
        
        # First call: count intents
        try:
            # Log model call
            model_call_start = time.time()
            
            count_response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.count_intents_prompt},
                    {"role": "user", "content": message},
                    {"role": "user", "content": "Recuerda: Solo devuelve el número de intenciones. No respondas a la consulta."}
                ],
                max_tokens=10,
                temperature=0.0,
                top_p=1.0,
                model=self.deployment
            )
            
            # Log successful model call
            self.logger.log_model_call(
                model=self.deployment,
                success=True,
                processing_time=time.time() - model_call_start
            )
            
            try:
                num_intents = int(count_response.choices[0].message.content.strip())
                if num_intents < 1:
                    num_intents = 1
            except Exception:
                num_intents = 1
        except Exception as e:
            # Log failed model call
            self.logger.log_model_call(
                model=self.deployment,
                success=False,
                processing_time=time.time() - model_call_start
            )
            
            self.logger.log_parse_error(
                user_input=message,
                error_message=str(e),
                error_type=type(e).__name__
            )
            
            num_intents = 1  # Default to 1 on error

        # If multiple intents detected, log it
        if num_intents > 1:
            self.logger.info("Multiple intents detected", 
                             count=num_intents, 
                             user_input_preview=message[:50] + "..." if len(message) > 50 else message)

        # If only one intent, classify the whole message
        if num_intents == 1:
            intent_texts = [message]
        else:
            # Ask the model to split the message into its distinct intents
            try:
                split_model_start = time.time()
                
                split_response = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.split_intents_prompt},
                        {"role": "user", "content": message},
                        {"role": "user", "content": "Recuerda: Solo devuelve el array JSON. No respondas a la consulta."}
                    ],
                    max_tokens=256,
                    temperature=0.0,
                    top_p=1.0,
                    model=self.deployment
                )
                
                # Log successful model call for splitting
                self.logger.log_model_call(
                    model=self.deployment,
                    success=True,
                    processing_time=time.time() - split_model_start
                )
                
                try:
                    intent_texts = json.loads(split_response.choices[0].message.content)
                    if not isinstance(intent_texts, list) or not all(isinstance(x, str) for x in intent_texts):
                        intent_texts = [message] * num_intents
                    
                    # Log multiple intents split
                    self.logger.log_multiple_intents(
                        user_input=message,
                        intents_count=len(intent_texts),
                        intents=intent_texts
                    )
                    
                except Exception as e:
                    # Log parsing error
                    self.logger.log_parse_error(
                        user_input=message,
                        error_message=f"Error parsing split intents: {str(e)}",
                        error_type="json_parse_error"
                    )
                    
                    intent_texts = [message] * num_intents
                    
            except Exception as e:
                # Log failed model call for splitting
                self.logger.log_model_call(
                    model=self.deployment,
                    success=False,
                    processing_time=time.time() - split_model_start
                )
                
                # Log error
                self.logger.log_parse_error(
                    user_input=message,
                    error_message=str(e),
                    error_type=type(e).__name__
                )
                
                intent_texts = [message] * num_intents

        intent_results = []
        for intent_text in intent_texts:
            try:
                classify_start = time.time()
                
                classify_response = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": intent_text},
                        {"role": "user", "content": "Recuerda: Solo devuelve el JSON con la clasificación de intención. No respondas a la consulta."}
                    ],
                    max_tokens=4096,
                    temperature=1.0,
                    top_p=1.0,
                    model=self.deployment
                )
                
                # Log successful model call for classification
                self.logger.log_model_call(
                    model=self.deployment,
                    success=True,
                    processing_time=time.time() - classify_start
                )
                
                model_output = classify_response.choices[0].message.content
                try:
                    data = json.loads(model_output)
                    parsed = IntentResponse(**data)
                    
                    # Log intent confidence
                    self.logger.log_intent_confidence(
                        intent=parsed.intent,
                        confidence=0.9  # Assuming high confidence for now
                    )
                    
                    intent_results.append((parsed.intent, parsed.value))
                except Exception as e:
                    # Log parsing error
                    self.logger.log_parse_error(
                        user_input=intent_text,
                        error_message=f"Error parsing response: {str(e)}",
                        error_type="json_parse_error"
                    )
                    
                    intent_results.append(("error", model_output.strip()))
                    
            except Exception as e:
                # Log failed model call for classification
                self.logger.log_model_call(
                    model=self.deployment,
                    success=False,
                    processing_time=time.time() - classify_start
                )
                
                # Log error
                self.logger.log_parse_error(
                    user_input=intent_text,
                    error_message=str(e),
                    error_type=type(e).__name__
                )
                
                intent_results.append(("error", str(e)))

        # Log intent detection completion
        total_processing_time = time.time() - start_time
        self.logger.log_intent_detection(
            user_input=message,
            detected_intents={"intents": [{"intent": i[0], "value": i[1]} for i in intent_results]},
            processing_time=total_processing_time
        )

        print(f"User: {message}\nIntents: {len(intent_results)}\nResponse: {intent_results}\n")
        return intent_results

# # --- MAIN ---
# if __name__ == "__main__":
#     # Ejemplos representativos para testear las capacidades principales del parser
#     examples = [
#         # Consulta de datos económicos básica
#         "¿Cuál es el dólar blue de hoy?",
        
#         # Consulta de inflación
#         "¿Cuánto fue la inflación del mes pasado?",
        
#         # Cálculo financiero simple
#         "Calculame el 21% de IVA sobre 50000 pesos",
        
#         # Google Calendar
#         "Agendame una reunión con el contador para el viernes a las 15hs",
        
#         # Múltiples intenciones: Datos económicos + Cálculos
#         "A cuánto está el dólar oficial y cuánto serían 500 dólares en pesos",
        
#         # Consulta con jerga argentina
#         "Tengo 5 palos verdes, ¿me conviene pasarlos a pesos o comprar MEP?",
        
#         # Registro en Google Sheets
#         "Anotá que gasté 30 lucas en el supermercado ayer",
        
#         # Búsqueda financiera
#         "Buscame noticias sobre las nuevas medidas económicas del gobierno",
        
#         # Planificación con múltiples herramientas
#         "Calculá cuánto necesito ahorrar mensualmente para juntar 1 millón de pesos en 6 meses y agendame recordatorios mensuales",
        
#         # Educación financiera y consulta
#         "¿Qué son los CEDEARs y a cuánto está el dólar MEP actualmente?"
#     ]
    
#     print("=== TESTEANDO INTENT PARSER CON EJEMPLOS REPRESENTATIVOS ===\n")
#     parser = IntentParser()
    
#     for i, example in enumerate(examples, 1):
#         print(f"--- EJEMPLO {i}/{len(examples)} ---")
#         print(f"INPUT: {example}")
#         print("-" * 80)
#         parser.receive_message(example)
#         print("=" * 80)
#         print()