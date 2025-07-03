import os  # Keep this import at the top
import sys
from openai import AzureOpenAI
from dotenv import load_dotenv
import pydantic
from pydantic import field_validator
import json
import time
import structlog  # Add this import
from typing import Optional, Union


class IntentResponse(pydantic.BaseModel):
    intent: str
    value: str
    depends_on: str = "independiente"  # REQUIRED field - dependency tool name or "independiente" for independent intents
    step: str = "final"  # REQUIRED field - "final" for user-facing actions, "intermedio" for preparatory steps
    
    @field_validator('depends_on', mode='before')
    @classmethod
    def validate_depends_on(cls, v):
        # Ensure depends_on is never null or empty string
        if v is None or v == "":
            return "independiente"
        return v
    
    @field_validator('step', mode='before')
    @classmethod
    def validate_step(cls, v):
        # Ensure step is always valid
        if v is None or v == "":
            return "final"
        if v not in ["final", "intermedio"]:
            return "final"  # Default to final for invalid values
        return v

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
            
            "🏦 SISTEMA MCP INTEGRADO - HERRAMIENTAS ESPECÍFICAS:\n"
            
            # "� 1. GOOGLE SHEETS (Hojas de Cálculo Financieras):\n"
            # "Herramientas disponibles:\n"
            # "   • get_sheet_data: Leer datos de hojas específicas\n"
            # "   • get_sheet_formulas: Obtener fórmulas de celdas\n"
            # "   • update_cells: Actualizar celdas específicas\n"
            # "   • batch_update_cells: Actualizar múltiples rangos\n"
            # "   • add_rows: Agregar filas a hojas\n"
            # "   • add_columns: Agregar columnas a hojas\n"
            # "   • list_sheets: Listar todas las hojas\n"
            # "   • copy_sheet: Copiar hojas existentes\n"
            # "   • rename_sheet: Renombrar hojas\n"
            # "   • get_multiple_sheet_data: Leer datos de múltiples hojas\n"
            # "   • get_multiple_spreadsheet_summary: Resumen de múltiples hojas\n"
            # "   • create_spreadsheet: Crear nuevas hojas de cálculo\n"
            # "   • create_sheet: Crear nuevas pestañas\n"
            # "   • list_spreadsheets: Listar todas las hojas de cálculo\n"
            # "   • share_spreadsheet: Compartir hojas de cálculo\n"
            
            # "� 2. GOOGLE CALENDAR (Gestión de Agenda):\n"
            # "Herramientas disponibles:\n"
            # "   • create_event: Crear eventos con detalles completos\n"
            # "   • list_events: Listar eventos por rango de fechas\n"
            # "   • update_event: Modificar eventos existentes\n"
            # "   • delete_event: Eliminar eventos\n"
            
            # "🧮 3. CALCULADORA (Cálculos Matemáticos):\n"
            # "Herramienta disponible:\n"
            # "   • calculate: Operaciones matemáticas y financieras precisas\n"
            
            # "🌐 4. TAVILY WEB SEARCH (Búsqueda e Investigación):\n"
            # "Herramientas disponibles:\n"
            # "   • tavily-search: Búsqueda web general con IA\n"
            # "   • tavily-extract: Extraer información específica de URLs\n"
            # "   • tavily-crawl: Rastrear sitios web para datos\n"
            # "   • tavily-map: Mapear y analizar contenido web\n"
            
            # "� 5. RAG (Retrieval-Augmented Generation):\n"
            # "Herramientas disponibles:\n"
            # "   • query_documents: Consultar documentos específicos\n"
            # "   • search_knowledge: Buscar en base de conocimiento\n"
            # "   • get_context: Obtener contexto relevante\n"
            # "   • analyze_content: Analizar contenido de documentos\n"
            
            # "💾 6. MEMORIA/CONTEXTO DE SESIÓN:\n"
            # "Herramientas disponibles:\n"
            # "   • store_preference: Guardar preferencias del usuario\n"
            # "   • retrieve_preference: Consultar preferencias guardadas\n"
            # "   • store_memory: Guardar información en memoria\n"
            # "   • search_memory: Buscar en memoria conversacional\n"
            # "   • get_session_history: Obtener historial de sesión\n"
            # "   • update_user_profile: Actualizar perfil del usuario\n"
            
            # "❓ 7. CONSULTAS GENERALES (Sin herramientas específicas):\n"
            # "Tipos de consulta:\n"
            # "   • general_query: Preguntas generales sin acciones específicas\n"
            # "   • financial_education: Explicaciones de conceptos financieros\n"
            # "   • advice_request: Consejos y recomendaciones financieras\n"
            # "   • conversational: Interacciones conversacionales simples\n"
            
            "🎯 MAPEO DE INTENCIONES A HERRAMIENTAS ESPECÍFICAS:\n"
            
            "� GOOGLE SHEETS:\n"
            "• get_sheet_data: Leer datos financieros, presupuestos, registros\n"
            "• get_sheet_formulas: Consultar fórmulas de cálculos financieros\n"
            "• update_cells: Modificar o sobreescribir celdas existentes\n"
            "• batch_update_cells: Actualizar múltiples registros\n"
            "• add_rows: Agregar nuevos registros financieros\n"
            "• add_columns: Expandir categorías de presupuesto\n"
            "• list_sheets: Ver todas las hojas financieras\n"
            "• copy_sheet: Duplicar plantillas de presupuesto\n"
            "• rename_sheet: Organizar hojas por período/categoría\n"
            "• get_multiple_sheet_data: Consolidar datos financieros\n"
            "• get_multiple_spreadsheet_summary: Resumen de portfolios\n"
            "• create_spreadsheet: Crear nuevos presupuestos/registros\n"
            "• create_sheet: Agregar nuevas pestañas temáticas\n"
            "• list_spreadsheets: Ver todas las hojas de cálculo\n"
            "• share_spreadsheet: Compartir presupuestos familiares\n"
            
            "📅 GOOGLE CALENDAR:\n"
            "• create_event: Agendar reuniones financieras, recordatorios\n"
            "• list_events: Ver agenda financiera, próximos vencimientos\n"
            "• update_event: Modificar citas con contador/asesor\n"
            "• delete_event: Cancelar reuniones financieras\n"
            
            "🧮 CALCULADORA:\n"
            "• calculate: Operaciones matemáticas, cálculos financieros, conversiones, porcentajes, intereses\n"
            
            "🌐 TAVILY WEB SEARCH:\n"
            "• tavily-search: Búsqueda de noticias económicas, información financiera\n"
            "• tavily-extract: Extraer datos específicos de sitios financieros\n"
            "• tavily-crawl: Investigar tendencias del mercado\n"
            "• tavily-map: Analizar información económica compleja\n"
            
            "📚 RAG:\n"
            "• query_documents: Consultar documentos económicos específicos\n"
            "• search_knowledge: Buscar conceptos financieros\n"
            "• get_context: Obtener contexto para consultas complejas\n"
            "• analyze_content: Analizar documentos financieros\n"
            
            "💾 MEMORIA/CONTEXTO:\n"
            "• store_preference: Guardar límites de gasto, objetivos financieros\n"
            "• retrieve_preference: Consultar configuraciones personales\n"
            "• store_memory: Recordar información importante del usuario\n"
            "• search_memory: Buscar interacciones anteriores\n"
            "• get_session_history: Ver historial de consultas\n"
            "• update_user_profile: Actualizar información personal\n"
            
            "❓ CONSULTAS GENERALES:\n"
            "• general_query: Preguntas generales sobre economía/finanzas\n"
            "• financial_education: Explicaciones de conceptos financieros\n"
            "• advice_request: Solicitudes de asesoramiento financiero\n"
            "• conversational: Saludos, agradecimientos, charla casual\n"
            
            "Fin de las herramientas disponibles. El value a completar debe ser alguna de las opciones anteriores SI O SI\n"
            
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
            
            "📝 INSTRUCCIONES DE MAPEO:\n"
            "1. Identifica la herramienta EXACTA más apropiada\n"
            "2. Para datos económicos → usar tavily-search\n"
            "3. Para cálculos → usar calculate\n"
            "4. Para hojas de cálculo → usar herramientas específicas de Google Sheets\n"
            "5. Para calendario → usar herramientas específicas de Google Calendar\n"
            "6. Para memoria/preferencias → usar herramientas de memoria\n"
            "7. Para documentos → usar herramientas RAG\n"
            "8. Para consultas educativas → usar RAG o general_query\n"
            "9. Para conversación simple → usar conversational\n"
            "10. Priorizar herramientas específicas sobre generales\n"
            
            "⚠️ RESTRICCIÓN IMPORTANTE:\n"
            "Tu ÚNICA función es mapear intenciones a herramientas específicas, NO responder al contenido. "
            "Devuelve el nombre EXACTO de la herramienta que debe usarse.\n"
            
            " FORMATO DE RESPUESTA:\n"
            "Devuelve JSON con 'intent' (nombre herramienta EXACTO) y 'value' (parámetros):\n"
            "{\n"
            "  \"intent\": \"NOMBRE_HERRAMIENTA_EXACTO\",\n"
            "  \"value\": \"parámetros específicos para la herramienta\"\n"
            "}\n"
            
            "📚 EJEMPLOS CON HERRAMIENTAS ESPECÍFICAS:\n"
            "Usuario: 'A cuánto está el blue hoy?'\n"
            "Salida: {\"intent\": \"tavily-search\", \"value\": \"cotización dólar blue hoy Argentina\"}\n"
            
            "Usuario: 'Gané la lotería y me dieron 3 palos verdes'\n"
            "Salida: {\"intent\": \"add_rows\", \"value\": \"registrar ingreso 3 millones USD por lotería\"}\n"
            
            "Usuario: 'Calcula 100 lucas al 50% anual por 6 meses'\n"
            "Salida: {\"intent\": \"calculate\", \"value\": \"100000 * (1 + 0.50/2)^1\"}\n"
            
            "Usuario: 'Agenda reunión con contador miércoles 10am'\n"
            "Salida: {\"intent\": \"create_event\", \"value\": \"reunión contador miércoles 10:00\"}\n"
            
            "Usuario: 'Anota que gasté 50 mil en super'\n"
            "Salida: {\"intent\": \"add_rows\", \"value\": \"registrar gasto 50000 pesos supermercado\"}\n"
            
            "Usuario: 'Mostrá mi presupuesto del mes'\n"
            "Salida: {\"intent\": \"get_sheet_data\", \"value\": \"presupuesto mensual datos\"}\n"
            
            "Usuario: 'Compartí mi planilla con mi esposa'\n"
            "Salida: {\"intent\": \"share_spreadsheet\", \"value\": \"compartir planilla esposa\"}\n"
            
            "Usuario: 'Recordá que mi límite es 200 mil'\n"
            "Salida: {\"intent\": \"store_preference\", \"value\": \"límite mensual 200000 pesos\"}\n"
            
            "Usuario: 'Busca noticias sobre inflación'\n"
            "Salida: {\"intent\": \"tavily-search\", \"value\": \"noticias inflación Argentina\"}\n"
            
            "Usuario: 'Qué es el carry trade?'\n"
            "Salida: {\"intent\": \"financial_education\", \"value\": \"carry trade concepto financiero\"}\n"
            
            "Usuario: 'Hola, cómo estás?'\n"
            "Salida: {\"intent\": \"conversational\", \"value\": \"saludo casual\"}\n"
            
            "Usuario: 'Qué me recomendás para invertir?'\n"
            "Salida: {\"intent\": \"advice_request\", \"value\": \"recomendaciones inversión\"}\n"
            
            "Usuario: 'Consultá mis documentos sobre plazo fijo'\n"
            "Salida: {\"intent\": \"query_documents\", \"value\": \"plazo fijo información documentos\"}\n"
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
            
            "REGLAS ESPECÍFICAS PARA REGISTRO DE TRANSACCIONES:\n"
            "- Si el usuario menciona recibir dinero, ganarlo o ingresos (ej: 'gané la lotería y me dieron X'), agrupa toda la información del ingreso en UNA sola intención\n"
            "- Si el usuario menciona gastos o egresos, agrupa toda la información del gasto en UNA sola intención\n"
            "- Las preguntas sobre qué hacer con el dinero son intenciones SEPARADAS\n"
            
            "IMPORTANTE: Tu ÚNICA tarea es dividir el mensaje en intenciones separadas. "
            "NO respondas a las consultas del usuario ni ofrezcas explicaciones o contenido adicional. "
            "Divide el mensaje en intenciones separadas, manteniendo el contexto argentino. "
            "Si el mensaje contiene múltiples preguntas unidas por 'o', 'y', 'además', 'también', divide cada una como intención separada. "
            "Devuelve un array JSON de strings. No expliques, solo devuelve el array.\n"
            
            "Ejemplos con contexto argentino:\n"
            "Usuario: 'Gané la lotería y me dieron 3 palos verdes. Me conviene pasarlos a pesos o invertir en bitcoin?'\n"
            "Salida: [\"Gané la lotería y me dieron 3 palos verdes\", \"Me conviene pasarlos a pesos?\", \"Me conviene invertir en bitcoin?\"]\n"
            
            "Usuario: 'Me dieron 2 palos verdes. Me conviene pasarlos a pesos o invertir en plazo fijo?'\n"
            "Salida: [\"Me dieron 2 palos verdes\", \"Me conviene pasarlos a pesos?\", \"Me conviene invertir en plazo fijo?\"]\n"
            
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

        self.expansion_prompt = (
            "Eres un experto en expansión de flujos de Google Sheets y Google Calendar para EconomIAssist. "
            "Tu tarea es expandir intenciones que requieren operaciones multi-paso y determinar cuál es el paso FINAL basándote en la intención REAL del usuario.\n"
            
            "🎯 HERRAMIENTAS GOOGLE SHEETS DISPONIBLES:\n"
            "• list_spreadsheets: Listar hojas de cálculo disponibles\n"
            "• list_sheets: Listar pestañas de una hoja específica\n"
            "• get_sheet_data: Leer datos de hojas específicas\n"
            "• add_rows: Agregar filas (registros financieros)\n"
            "• update_cells: Actualizar celdas específicas\n"
            "• batch_update_cells: Actualizar múltiples rangos\n"
            "• create_sheet: Crear nuevas pestañas\n"
            "• share_spreadsheet: Compartir hojas de cálculo\n"
            "• copy_sheet: Copiar hojas existentes\n"
            "• rename_sheet: Renombrar hojas\n"
            
            "🎯 HERRAMIENTAS GOOGLE CALENDAR DISPONIBLES:\n"
            "• create_event: Crear eventos\n"
            "• update_event: Actualizar eventos\n"
            "• list_events: Listar eventos\n"
            "• delete_event: Eliminar eventos\n"
            
            "🧠 ANÁLISIS CONTEXTUAL PARA DETERMINAR PASO FINAL:\n"
            "Analiza QUÉ está pidiendo realmente el usuario para determinar cuál es la acción final:\n"
            
            "EJEMPLOS DE INTENCIÓN REAL:\n"
            "• 'Listar archivos' → FINAL: list_spreadsheets\n"
            "• 'Listar hojas de un archivo' → list_spreadsheets (intermedio) + FINAL: list_sheets\n"
            "• 'Ver mis datos' → list_spreadsheets + list_sheets + FINAL: get_sheet_data\n"
            "• 'Anotar gasto' → list_spreadsheets + list_sheets + get_sheet_data + FINAL: add_rows\n"
            "• 'Actualizar registro' → list_spreadsheets + list_sheets + get_sheet_data + FINAL: update_cells\n"
            "• 'Crear nueva pestaña' → list_spreadsheets + FINAL: create_sheet\n"
            "• 'Compartir planilla' → FINAL: share_spreadsheet\n"
            "• 'Ver agenda' → FINAL: list_events\n"
            "• 'Agendar reunión' → tavily-search (fecha actual) + FINAL: create_event\n"
            
            "⚠️ REGLAS DE EXPANSIÓN CONTEXTUAL:\n"
            "1. IDENTIFICA la intención REAL del usuario (qué quiere lograr)\n"
            "2. DETERMINA cuál herramienta satisface directamente esa intención (esa es FINAL)\n"
            "3. AGREGA solo los pasos previos necesarios (esos son INTERMEDIO)\n"
            "4. Para operaciones de escritura (add_rows, update_cells): incluye navegación completa\n"
            "5. Para operaciones de lectura: incluye solo la navegación necesaria hasta llegar al objetivo\n"
            "6. Para create_event/update_event: incluye tavily-search para fechas relativas\n"
            "7. Para herramientas que no requieren expansión: mantener como FINAL único\n"
            
            "🎯 CLASIFICACIÓN DE PASOS (CONTEXTUAL):\n"
            "- 'intermedio': Pasos que PREPARAN para llegar al objetivo del usuario\n"
            "- 'final': El paso que CUMPLE directamente lo que pidió el usuario\n"
            
            "📝 FORMATO DE RESPUESTA:\n"
            "Devuelve un array JSON con las intenciones expandidas. Cada intención debe tener:\n"
            "- 'intent': nombre exacto de la herramienta\n"
            "- 'value': descripción específica de la acción\n"
            "- 'step': 'intermedio' o 'final' según la intención REAL del usuario\n"
            
            "🇦🇷 EJEMPLOS DE EXPANSIÓN CONTEXTUAL:\n"
            
            "Input: [{\"intent\": \"list_spreadsheets\", \"value\": \"listar archivos disponibles\"}]\n"
            "Análisis: Usuario quiere VER archivos → list_spreadsheets es el objetivo final\n"
            "Output: [{\"intent\": \"list_spreadsheets\", \"value\": \"listar archivos disponibles\", \"step\": \"final\"}]\n"
            
            "Input: [{\"intent\": \"list_sheets\", \"value\": \"listar hojas de archivo financiero\"}]\n"
            "Análisis: Usuario quiere VER hojas → necesita navegar a archivo primero, luego listar hojas\n"
            "Output: [\n"
            "  {\"intent\": \"list_spreadsheets\", \"value\": \"listar hojas de cálculo disponibles\", \"step\": \"intermedio\"},\n"
            "  {\"intent\": \"list_sheets\", \"value\": \"listar hojas de archivo financiero\", \"step\": \"final\"}\n"
            "]\n"
            
            "Input: [{\"intent\": \"get_sheet_data\", \"value\": \"presupuesto mensual datos\"}]\n"
            "Análisis: Usuario quiere VER datos → necesita navegar hasta la hoja específica\n"
            "Output: [\n"
            "  {\"intent\": \"list_spreadsheets\", \"value\": \"listar hojas de cálculo disponibles\", \"step\": \"intermedio\"},\n"
            "  {\"intent\": \"list_sheets\", \"value\": \"listar pestañas de la hoja seleccionada\", \"step\": \"intermedio\"},\n"
            "  {\"intent\": \"get_sheet_data\", \"value\": \"presupuesto mensual datos\", \"step\": \"final\"}\n"
            "]\n"
            
            "Input: [{\"intent\": \"add_rows\", \"value\": \"registrar gasto 50000 pesos supermercado\"}]\n"
            "Análisis: Usuario quiere REGISTRAR gasto → necesita navegación completa + estructura\n"
            "Output: [\n"
            "  {\"intent\": \"list_spreadsheets\", \"value\": \"listar hojas de cálculo disponibles\", \"step\": \"intermedio\"},\n"
            "  {\"intent\": \"list_sheets\", \"value\": \"listar pestañas de la hoja seleccionada\", \"step\": \"intermedio\"},\n"
            "  {\"intent\": \"get_sheet_data\", \"value\": \"obtener encabezados y estructura de la hoja\", \"step\": \"intermedio\"},\n"
            "  {\"intent\": \"add_rows\", \"value\": \"registrar gasto 50000 pesos supermercado\", \"step\": \"final\"}\n"
            "]\n"
            
            "Input: [{\"intent\": \"create_sheet\", \"value\": \"nueva pestaña gastos diciembre\"}]\n"
            "Análisis: Usuario quiere CREAR pestaña → necesita acceso al archivo primero\n"
            "Output: [\n"
            "  {\"intent\": \"list_spreadsheets\", \"value\": \"listar hojas de cálculo disponibles\", \"step\": \"intermedio\"},\n"
            "  {\"intent\": \"create_sheet\", \"value\": \"nueva pestaña gastos diciembre\", \"step\": \"final\"}\n"
            "]\n"
            
            "Input: [{\"intent\": \"share_spreadsheet\", \"value\": \"compartir planilla esposa\"}]\n"
            "Análisis: Usuario quiere COMPARTIR → share_spreadsheet es el objetivo directo\n"
            "Output: [{\"intent\": \"share_spreadsheet\", \"value\": \"compartir planilla esposa\", \"step\": \"final\"}]\n"
            
            "Input: [{\"intent\": \"list_events\", \"value\": \"ver agenda próxima semana\"}]\n"
            "Análisis: Usuario quiere VER agenda → list_events es el objetivo directo\n"
            "Output: [{\"intent\": \"list_events\", \"value\": \"ver agenda próxima semana\", \"step\": \"final\"}]\n"
            
            "Input: [{\"intent\": \"create_event\", \"value\": \"reunión contador mañana 10am\"}]\n"
            "Análisis: Usuario quiere AGENDAR → necesita fecha actual para interpretar 'mañana'\n"
            "Output: [\n"
            "  {\"intent\": \"tavily-search\", \"value\": \"fecha actual Argentina hoy\", \"step\": \"intermedio\"},\n"
            "  {\"intent\": \"create_event\", \"value\": \"reunión contador mañana 10am\", \"step\": \"final\"}\n"
            "]\n"
            
            "Input: [{\"intent\": \"calculate\", \"value\": \"100000 * 1.5\"}]\n"
            "Análisis: Usuario quiere CALCULAR → no requiere expansión\n"
            "Output: [{\"intent\": \"calculate\", \"value\": \"100000 * 1.5\", \"step\": \"final\"}]\n"
            
            "Input: [{\"intent\": \"tavily-search\", \"value\": \"cotización dólar blue\"}, {\"intent\": \"add_rows\", \"value\": \"registrar compra dólares\"}]\n"
            "Análisis: Usuario quiere BUSCAR cotización Y REGISTRAR compra → dos objetivos separados\n"
            "Output: [\n"
            "  {\"intent\": \"tavily-search\", \"value\": \"cotización dólar blue\", \"step\": \"final\"},\n"
            "  {\"intent\": \"list_spreadsheets\", \"value\": \"listar hojas de cálculo disponibles\", \"step\": \"intermedio\"},\n"
            "  {\"intent\": \"list_sheets\", \"value\": \"listar pestañas de la hoja seleccionada\", \"step\": \"intermedio\"},\n"
            "  {\"intent\": \"get_sheet_data\", \"value\": \"obtener encabezados y estructura de la hoja\", \"step\": \"intermedio\"},\n"
            "  {\"intent\": \"add_rows\", \"value\": \"registrar compra dólares\", \"step\": \"final\"}\n"
            "]\n"
            
            "🎯 REGLAS FINALES:\n"
            "1. ANALIZA qué quiere lograr el usuario (su intención real)\n"
            "2. IDENTIFICA cuál herramienta cumple directamente esa intención\n"
            "3. ESA herramienta es el paso 'final'\n"
            "4. AGREGA solo los pasos previos necesarios como 'intermedio'\n"
            "5. Para herramientas sin expansión: siempre 'final'\n"
            "6. Para múltiples intenciones: analiza cada una por separado\n"
        )

        self.dependency_prompt = (
            "Eres un experto en analizar mensajes de usuarios para EconomIAssist, un asistente financiero argentino. "
            "Tu tarea es detectar DEPENDENCIAS LÓGICAS entre intenciones cuando una acción necesita el resultado de otra para ejecutarse correctamente.\n"
            
            "⚠️ REGLAS CRÍTICAS:\n"
            "1. DEBES mantener EXACTAMENTE la misma cantidad de intenciones que recibiste\n"
            "2. NO elimines ni combines intenciones\n"
            "3. NO modifiques los campos 'intent', 'value' y 'step' - cópialos EXACTAMENTE como los recibiste\n"
            "4. SOLO agrega el campo 'depends_on' a cada intención\n"
            "5. El campo 'depends_on' DEBE estar presente en TODAS las intenciones:\n"
            "   - Si hay dependencia: nombre exacto de la herramienta de la cual depende\n"
            "   - Si NO hay dependencia: ÚNICAMENTE \"independiente\" (nunca null, vacío, ni otro valor)\n"
            "6. IMPORTANTE: Para intenciones independientes usa EXCLUSIVAMENTE la palabra \"independiente\"\n"
            "7. PRESERVA el campo 'step' exactamente como lo recibiste\n"
            
            "Si recibes intenciones expandidas de Google Sheets (ej: list_spreadsheets → list_sheets → add_rows), "
            "mantén esa secuencia completa con las dependencias apropiadas.\n"
            "Si recibes intenciones expandidas de Google Calendar (ej: tavily-search → create_event), "
            "mantén esa secuencia completa con las dependencias apropiadas.\n"
            
            "🧠 ANÁLISIS CONTEXTUAL:\n"
            "No te limites a buscar palabras específicas. Analiza el CONTEXTO y la LÓGICA de la consulta:\n"
            "- ¿Una acción necesita información de la otra?\n"
            "- ¿El orden de ejecución es importante?\n"
            "- ¿Una tarea no tiene sentido sin el resultado de la anterior?\n"
            "- ¿El usuario implica una secuencia lógica?\n"
            "- Para secuencias de Google Sheets: list_spreadsheets → list_sheets → get_sheet_data → [acción principal]\n"
            "- Para secuencias de Google Calendar: tavily-search → [acción principal]\n"
            "- get_sheet_data verifica encabezados y estructura antes de manipular datos\n"
            "- tavily-search obtiene fecha actual para resolver referencias temporales relativas\n"
            
            "📝 FORMATO DE RESPUESTA:\n"
            "Devuelve un array JSON con TODAS las intenciones recibidas, cada una con:\n"
            "- 'intent': copia EXACTA del nombre de herramienta recibido\n"
            "- 'value': copia EXACTA de la descripción recibida\n"
            "- 'step': copia EXACTA del campo step recibido ('intermedio' o 'final')\n"
            "- 'depends_on': OBLIGATORIO - nombre de la herramienta de dependencia o \"independiente\" si no hay\n"
            
            "🇦🇷 EJEMPLOS CON ANÁLISIS CONTEXTUAL:\n"
            
            "Input: 4 intenciones expandidas\n"
            "Output: EXACTAMENTE 4 intenciones con depends_on OBLIGATORIO\n"
            
            "Usuario: 'Buscá el precio del blue y calculá cuánto son 500 lucas en dólares'\n"
            "Input: [{\"intent\": \"tavily-search\", \"value\": \"precio dólar blue\", \"step\": \"final\"}, {\"intent\": \"calculate\", \"value\": \"500000 pesos a dólares\", \"step\": \"final\"}]\n"
            "Análisis: El cálculo NECESITA el precio actual para ser preciso\n"
            "Salida: [{\"intent\": \"tavily-search\", \"value\": \"precio dólar blue\", \"step\": \"final\", \"depends_on\": \"independiente\"}, "
            "{\"intent\": \"calculate\", \"value\": \"500000 pesos a dólares\", \"step\": \"final\", \"depends_on\": \"tavily-search\"}]\n"
            
            "Usuario: 'Anota que gasté 50 mil en super' (expandido)\n"
            "Input: [{\"intent\": \"list_spreadsheets\", \"value\": \"listar hojas disponibles\", \"step\": \"intermedio\"}, "
            "{\"intent\": \"list_sheets\", \"value\": \"listar pestañas\", \"step\": \"intermedio\"}, "
            "{\"intent\": \"get_sheet_data\", \"value\": \"obtener encabezados y estructura\", \"step\": \"intermedio\"}, "
            "{\"intent\": \"add_rows\", \"value\": \"registrar gasto 50000 pesos supermercado\", \"step\": \"final\"}]\n"
            "Análisis: Secuencia lógica de Google Sheets, cada paso depende del anterior\n"
            "Salida: [{\"intent\": \"list_spreadsheets\", \"value\": \"listar hojas disponibles\", \"step\": \"intermedio\", \"depends_on\": \"independiente\"}, "
            "{\"intent\": \"list_sheets\", \"value\": \"listar pestañas\", \"step\": \"intermedio\", \"depends_on\": \"list_spreadsheets\"}, "
            "{\"intent\": \"get_sheet_data\", \"value\": \"obtener encabezados y estructura\", \"step\": \"intermedio\", \"depends_on\": \"list_sheets\"}, "
            "{\"intent\": \"add_rows\", \"value\": \"registrar gasto 50000 pesos supermercado\", \"step\": \"final\", \"depends_on\": \"get_sheet_data\"}]\n"
            
            "Usuario: 'Mirá mi agenda y buscá noticias económicas'\n"
            "Input: [{\"intent\": \"list_events\", \"value\": \"ver agenda\", \"step\": \"final\"}, {\"intent\": \"tavily-search\", \"value\": \"noticias económicas\", \"step\": \"final\"}]\n"
            "Análisis: Son acciones independientes, no hay dependencia lógica\n"
            "Salida: [{\"intent\": \"list_events\", \"value\": \"ver agenda\", \"step\": \"final\", \"depends_on\": \"independiente\"}, "
            "{\"intent\": \"tavily-search\", \"value\": \"noticias económicas\", \"step\": \"final\", \"depends_on\": \"independiente\"}]\n"
            
            "Usuario: 'Agenda reunión contador mañana 10am' (expandido)\n"
            "Input: [{\"intent\": \"tavily-search\", \"value\": \"fecha actual Argentina hoy\", \"step\": \"intermedio\"}, "
            "{\"intent\": \"create_event\", \"value\": \"reunión contador mañana 10am\", \"step\": \"final\"}]\n"
            "Análisis: create_event NECESITA la fecha actual para interpretar 'mañana' correctamente\n"
            "Salida: [{\"intent\": \"tavily-search\", \"value\": \"fecha actual Argentina hoy\", \"step\": \"intermedio\", \"depends_on\": \"independiente\"}, "
            "{\"intent\": \"create_event\", \"value\": \"reunión contador mañana 10am\", \"step\": \"final\", \"depends_on\": \"tavily-search\"}]\n"
            
            "🧩 CRITERIOS DE DEPENDENCIA:\n"
            "1. ¿El resultado de A es NECESARIO para ejecutar B correctamente?\n"
            "2. ¿B sería impreciso o incompleto sin A?\n"
            "3. ¿El contexto implica una secuencia lógica obligatoria?\n"
            "4. ¿El usuario está pidiendo algo que se construye sobre información previa?\n"
            
            "🚨 IMPORTANTE:\n"
            "- MANTÉN la cantidad exacta de intenciones recibidas\n"
            "- COPIA exactamente los campos 'intent', 'value' y 'step' sin modificarlos\n"
            "- El campo 'depends_on' DEBE estar presente en TODAS las intenciones\n"
            "- El campo 'step' DEBE preservarse exactamente como lo recibiste\n"
            "- Para independientes usa ÚNICAMENTE: \"independiente\" (nunca null, \"\", none, o independente)\n"
            "- Para dependientes usa: el nombre EXACTO de la herramienta de dependencia\n"
            "- NO uses valores como null, vacío, none, o variaciones de \"independiente\"\n"
            "- Analiza el SENTIDO LÓGICO, no solo las palabras\n"
            "- Reconoce jerga argentina: 'lucas' (miles), 'palos verdes' (millones USD), 'blue' (dólar paralelo)\n"
        )

        # Set the logger as an alias to intent_logger
        self.logger = self.intent_logger
    
    def receive_message(self, message: str):
        """
        Detect and split multiple intents from a single user input, including dependencies.
        4-step process: Split -> Map -> Expand (Google Sheets & Calendar) -> Dependencies
        Returns a list of intents with dependency information.
        """
        
        self.logger.info("Intent parsing pipeline initiated", 
                        user_message=message, 
                        message_length=len(message),
                        pipeline_steps=["split", "map", "expand", "dependencies"])
        
        # STEP 1: Split message into separate intents (combines counting and splitting)
        try:
            self.logger.info("Step 1 started: Analyzing and splitting user message into atomic intents", 
                           step="split_intents", 
                           input_message=message[:100] + "..." if len(message) > 100 else message)
            split_response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.split_intents_prompt},
                    {"role": "user", "content": message},
                ],
                max_tokens=128,
                temperature=0.0,
                top_p=1.0,
                model=self.deployment
            )
            split_intents = json.loads(split_response.choices[0].message.content)
            if not isinstance(split_intents, list):
                raise ValueError("Split response is not a list")
            
            num_intents = len(split_intents)
            self.logger.info("Step 1 completed: Message successfully split into atomic intents", 
                           step="split_intents",
                           step_status="success",
                           original_message=message,
                           split_intents=split_intents, 
                           num_intents_detected=num_intents,
                           llm_tokens_used=128,
                           next_step="mapping_to_tools")
            
        except Exception as e:
            self.logger.log_parse_error(
                user_input=message,
                error_message=f"Error en división: {str(e)}",
                error_type=type(e).__name__
            )
            split_intents = [message]
            num_intents = 1
            self.logger.warning("Step 1 failed: Falling back to treating entire message as single intent", 
                              step="split_intents",
                              step_status="failed_with_fallback",
                              error_type=type(e).__name__,
                              error_details=str(e),
                              fallback_strategy="single_intent",
                              fallback_intents=split_intents, 
                              recovery_action="proceeding_with_mapping")

        # STEP 2: Map each split intent to specific tools using system prompt
        try:
            self.logger.info("Step 2 started: Mapping each intent to specific MCP tools and capabilities", 
                           step="map_intents",
                           intents_to_map=split_intents,
                           num_intents_to_process=len(split_intents),
                           available_tool_categories=["google_sheets", "google_calendar", "tavily_search", "calculator", "rag", "memory", "general"])
            mapped_intents = []
            
            for i, intent_text in enumerate(split_intents):
                mapping_response = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": intent_text},
                    ],
                    max_tokens=64,
                    temperature=0.0,
                    top_p=1.0,
                    model=self.deployment
                )
                
                try:
                    mapped_intent = json.loads(mapping_response.choices[0].message.content)
                    if isinstance(mapped_intent, dict) and "intent" in mapped_intent and "value" in mapped_intent:
                        mapped_intents.append(mapped_intent)
                    else:
                        raise ValueError("Invalid mapping format")
                except json.JSONDecodeError:
                    # Fallback if response is not JSON
                    mapped_intents.append({"intent": "general_query", "value": intent_text})
            
            self.logger.info("Step 2 completed: All intents successfully mapped to specific tools", 
                           step="map_intents",
                           step_status="success",
                           mapped_intents=mapped_intents, 
                           num_original_intents=len(split_intents),
                           num_mapped_intents=len(mapped_intents),
                           mapping_success_rate="100%",
                           next_step="expansion_for_multi_step_flows")
            
        except Exception as e:
            self.logger.log_parse_error(
                user_input=message,
                error_message=f"Error en mapeo: {str(e)}",
                error_type=type(e).__name__
            )
            mapped_intents = [{"intent": "general_query", "value": message}]
            self.logger.warning("Step 2 failed: Falling back to general query for entire message", 
                              step="map_intents",
                              step_status="failed_with_fallback",
                              error_type=type(e).__name__,
                              error_details=str(e),
                              fallback_strategy="general_query",
                              fallback_intents=mapped_intents,
                              recovery_action="proceeding_with_expansion")

        # STEP 2.5: Expand Google Sheets and Calendar intents into multi-step sequences
        try:
            self.logger.info("Step 2.5 started: Expanding multi-step workflows for Google Sheets and Calendar operations", 
                           step="expand_intents",
                           intents_before_expansion=mapped_intents,
                           num_intents_to_analyze=len(mapped_intents),
                           expansion_rules={"google_sheets": "list_spreadsheets → list_sheets → get_sheet_data → action", 
                                          "google_calendar": "tavily-search(current_date) → action"},
                           supports_expansion=["add_rows", "update_cells", "batch_update_cells", "create_event", "update_event"])
            
            expansion_response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.expansion_prompt},
                    {"role": "user", "content": json.dumps(mapped_intents, ensure_ascii=False)},
                ],
                max_tokens=512,
                temperature=0.0,
                top_p=1.0,
                model=self.deployment
            )
            
            expanded_intents = json.loads(expansion_response.choices[0].message.content)
            if not isinstance(expanded_intents, list) or not all(isinstance(x, dict) for x in expanded_intents):
                raise ValueError("Invalid expansion format")
            
            # Ensure all expanded intents have the "step" field
            for intent in expanded_intents:
                if "step" not in intent:
                    # Default to "final" if step field is missing
                    intent["step"] = "final"
                    self.logger.warning("Added missing step field", 
                                      intent_name=intent.get("intent", "unknown"),
                                      assigned_step="final")
                
            expansion_ratio = len(expanded_intents) / len(mapped_intents) if mapped_intents else 1
            self.logger.info("Step 2.5 completed: Multi-step workflows successfully expanded for complex operations", 
                           step="expand_intents",
                           step_status="success",
                           intents_before_expansion=mapped_intents,
                           expanded_intents=expanded_intents, 
                           num_before_expansion=len(mapped_intents),
                           num_after_expansion=len(expanded_intents),
                           expansion_ratio=f"{expansion_ratio:.2f}x",
                           expansion_added=len(expanded_intents) - len(mapped_intents),
                           next_step="dependency_analysis")
            
        except Exception as e:
            self.logger.log_parse_error(
                user_input=message,
                error_message=f"Error en expansión: {str(e)}",
                error_type=type(e).__name__
            )
            # Use mapped intents without expansion as fallback
            expanded_intents = mapped_intents
            # Ensure all fallback intents have the "step" field
            for intent in expanded_intents:
                if "step" not in intent:
                    intent["step"] = "final"  # Non-expanded intents are always final
            
            self.logger.warning("Step 2.5 failed: Proceeding without multi-step expansion", 
                              step="expand_intents",
                              step_status="failed_with_fallback",
                              error_type=type(e).__name__,
                              error_details=str(e),
                              fallback_strategy="no_expansion",
                              fallback_intents=expanded_intents,
                              impact="workflows_may_be_incomplete",
                              recovery_action="proceeding_with_dependency_analysis")

        # STEP 3: Detect dependencies between expanded intents
        try:
            self.logger.info("Step 3 started: Analyzing logical dependencies and execution order between intents", 
                           step="analyze_dependencies",
                           intents_to_analyze=expanded_intents,
                           num_intents_for_dependency_analysis=len(expanded_intents),
                           dependency_types=["sequential_google_sheets", "sequential_google_calendar", "data_dependent", "independent"],
                           analysis_scope="logical_flow_optimization")
            
            # Create a combined message with all expanded intents for dependency analysis
            dependency_input = {
                "original_message": message,
                "mapped_intents": expanded_intents
            }
            
            dependency_response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.dependency_prompt},
                    {"role": "user", "content": json.dumps(dependency_input, ensure_ascii=False)},
                ],
                max_tokens=512,
                temperature=0.0,
                top_p=1.0,
                model=self.deployment
            )
            
            final_intents = json.loads(dependency_response.choices[0].message.content)
            if not isinstance(final_intents, list) or not all(isinstance(x, dict) for x in final_intents):
                raise ValueError("Invalid dependency format")
            
            # CRITICAL: Ensure depends_on field is always present and valid
            for intent in final_intents:
                if "depends_on" not in intent or intent["depends_on"] is None or intent["depends_on"] == "":
                    intent["depends_on"] = "independiente"
                    self.logger.warning("Fixed missing or null depends_on field", 
                                      intent_name=intent.get("intent", "unknown"),
                                      corrected_to="independiente")
                
                # Ensure step field is preserved from expansion
                if "step" not in intent:
                    intent["step"] = "final"  # Default to final if missing
                    self.logger.warning("Added missing step field in dependency analysis", 
                                      intent_name=intent.get("intent", "unknown"),
                                      assigned_step="final")
                
            # Analyze dependency structure for logging
            independent_count = sum(1 for intent in final_intents if intent.get("depends_on") == "independiente")
            dependent_count = len(final_intents) - independent_count
            
            self.logger.info("Step 3 completed: Dependency analysis finished, execution order determined", 
                           step="analyze_dependencies",
                           step_status="success",
                           final_intents=final_intents, 
                           num_total_intents=len(final_intents),
                           num_independent_intents=independent_count,
                           num_dependent_intents=dependent_count,
                           dependency_preservation="exact_count_maintained",
                           execution_optimization="ready_for_sequential_processing")
            
            self.logger.log_multiple_intents(
                user_input=message,
                intents_count=len(final_intents),
                intents=final_intents
            )
            
        except Exception as e:
            self.logger.log_parse_error(
                user_input=message,
                error_message=f"Error en dependencias: {str(e)}",
                error_type=type(e).__name__
            )
            # Use expanded intents without dependencies as fallback
            final_intents = expanded_intents
            # CRITICAL: Ensure all fallback intents have proper depends_on field
            for intent in final_intents:
                if "depends_on" not in intent:
                    intent["depends_on"] = "independiente"
                # Ensure step field is preserved from expansion
                if "step" not in intent:
                    intent["step"] = "final"  # Default to final if missing
            
            self.logger.warning("Step 3 failed: Proceeding without dependency information", 
                              step="analyze_dependencies",
                              step_status="failed_with_fallback",
                              error_type=type(e).__name__,
                              error_details=str(e),
                              fallback_strategy="no_dependencies",
                              fallback_intents=final_intents,
                              impact="execution_order_not_optimized",
                              recovery_action="completing_pipeline_with_basic_intents")
        
        # Calculate pipeline metrics for final summary
        pipeline_success = all([
            len(split_intents) > 0,
            len(mapped_intents) > 0, 
            len(expanded_intents) > 0,
            len(final_intents) > 0
        ])
        
        self.logger.info("Intent parsing pipeline completed successfully", 
                        pipeline_status="completed",
                        pipeline_success=pipeline_success,
                        original_message=message,
                        final_intents=final_intents, 
                        total_final_intents=len(final_intents),
                        pipeline_metrics={
                            "input_message_length": len(message),
                            "split_intents_count": len(split_intents),
                            "mapped_intents_count": len(mapped_intents), 
                            "expanded_intents_count": len(expanded_intents),
                            "final_intents_count": len(final_intents),
                            "expansion_factor": len(expanded_intents) / len(mapped_intents) if mapped_intents else 1
                        },
                        ready_for_execution=True)
        return [IntentResponse(**intent) for intent in final_intents]

# # --- MAIN ---
# if __name__ == "__main__":
#     examples = [
#         # Ejemplo 1: Listar archivos (debe ser FINAL: list_spreadsheets)
#         "Qué archivos tengo disponibles?",
        
#         # Ejemplo 2: Listar hojas (debe ser: list_spreadsheets intermedio + list_sheets FINAL)
#         "Mostrá las hojas de mi archivo financiero",
        
#         # Ejemplo 3: Ver datos (debe ser: navegación + get_sheet_data FINAL)
#         "Mostrá mi presupuesto del mes",
        
#         # Ejemplo 4: Registro de gasto (debe expandir Google Sheets completo)
#         "Anota que gasté 150 lucas en supermercado ayer",
        
#         # Ejemplo 5: Consulta económica con cálculo dependiente
#         "Cuánto está el blue hoy y calcula cuánto son 300 mil pesos en dólares",
        
#         # Ejemplo 6: Agendar evento (debe expandir Google Calendar)
#         "Agenda reunión con contador mañana 3pm para revisar mis inversiones"
#     ]
    
#     parser = IntentParser()
#     print("🧪 Probando Intent Parser con lógica contextual mejorada\n")
    
#     for i, example in enumerate(examples, 1):
#         print(f"\n{'='*60}")
#         print(f"📋 EJEMPLO {i}: {example}")
#         print('='*60)
        
#         try:
#             intents = parser.receive_message(example)
#             print(f"\n✅ RESULTADO FINAL ({len(intents)} intenciones):")
            
#             # Separate intermediate and final steps for better visualization
#             intermediate_steps = []
#             final_steps = []
            
#             for j, intent in enumerate(intents, 1):
#                 step_emoji = "🔧" if intent.step == "intermedio" else "🎯"
#                 step_description = f"{step_emoji} [{intent.step.upper()}]"
                
#                 print(f"   {j}. {intent.intent} → '{intent.value}'")
#                 print(f"      └─ {step_description} | depends_on: {intent.depends_on}")
                
#                 if intent.step == "intermedio":
#                     intermediate_steps.append(intent.intent)
#                 else:
#                     final_steps.append(intent.intent)
            
#             # Summary
#             print(f"\n📊 RESUMEN:")
#             print(f"   • Pasos intermedios: {len(intermediate_steps)} ({', '.join(intermediate_steps) if intermediate_steps else 'ninguno'})")
#             print(f"   • Pasos finales: {len(final_steps)} ({', '.join(final_steps)})")
#             print(f"   • El agente responderá solo a: {', '.join(final_steps)}")
            
#         except Exception as e:
#             print(f"❌ Error procesando ejemplo {i}: {e}")
    
#     print(f"\n🏁 Pruebas completadas!")
#     print(f"\n🔧 = Paso intermedio (ejecutar silenciosamente)")
#     print(f"🎯 = Paso final (generar respuesta al usuario)")