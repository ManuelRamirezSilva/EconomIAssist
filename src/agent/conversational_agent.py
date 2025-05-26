#!/usr/bin/env python3
"""
Agente Conversacional Modular - OpenAI Agents SDK con MCP Real
Implementación completa con conexión real a servidores MCP externos
"""

import asyncio
import os
import sys
import json
import warnings
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import structlog
from dotenv import load_dotenv

# Suprimir warnings de tracing del OpenAI SDK
warnings.filterwarnings("ignore")
os.environ["OPENAI_LOG_LEVEL"] = "ERROR"

# Forzar recarga de variables de entorno
for key in list(os.environ.keys()):
    if key.startswith('AZURE_OPENAI_') or key.startswith('TAVILY_'):
        del os.environ[key]

# Cargar variables de entorno
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(env_path, override=True)

# OpenAI Agents SDK imports
from agents import Agent, Runner
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncAzureOpenAI

# Importar cliente MCP real
from .mcp_client import MCPManager

# Configurar logging estructurado
logger = structlog.get_logger()

# Suprimir logs de OpenAI durante ejecución
import logging
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

@dataclass
class MCPServerConfig:
    """Configuración de un servidor MCP"""
    name: str
    path: str
    description: str
    capabilities: List[str]

class AzureOpenAIConfig:
    """Configuración para Azure OpenAI"""
    
    def __init__(self):
        self.api_base = os.getenv("AZURE_OPENAI_API_BASE")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        
        if not all([self.api_base, self.api_key, self.api_version, self.deployment_name]):
            raise ValueError("Faltan credenciales de Azure OpenAI en el archivo .env")
        
        print(f"✅ Azure OpenAI configurado:")
        print(f"   📍 Endpoint: {self.api_base}")
        print(f"   🤖 Deployment: {self.deployment_name}")
        print(f"   🔑 API Version: {self.api_version}")
    
    def create_client(self) -> AsyncAzureOpenAI:
        """Crea un cliente de Azure OpenAI"""
        return AsyncAzureOpenAI(
            azure_endpoint=self.api_base,
            api_key=self.api_key,
            api_version=self.api_version
        )
    
    def create_model(self) -> OpenAIChatCompletionsModel:
        """Crea un modelo OpenAI configurado para Azure"""
        client = self.create_client()
        return OpenAIChatCompletionsModel(
            model=self.deployment_name,  # Usar deployment name correcto
            openai_client=client
        )

class IntentClassifier: ###MAXI WORK HERE
    """Clasificador de intenciones usando NLP para routing"""
    
    INTENT_PATTERNS = {
        'financial_query': [
            'saldo', 'dinero', 'cuenta', 'balance', 'cuanto tengo',
            'estado financiero', 'resumen'
        ],
        'financial_action': [
            'registra', 'anota', 'guarda', 'gasto', 'ingreso', 
            'transaccion', 'pago', 'compra'
        ],
        'rag_query': [
            'consejo', 'como', 'que es', 'explicame', 'ayuda con',
            'informacion', 'aprende', 'enseñame'
        ],
        'help': [
            'ayuda', 'help', 'que puedes hacer', 'comandos', 'funciones'
        ],
        'multi_intent': [
            'y tambien', 'ademas', 'despues', 'luego'
        ]
    }
    
    def classify_intent(self, text: str) -> Dict[str, float]:
        """
        Clasifica intenciones con scores de confianza
        Retorna un diccionario con intención -> score
        """
        text_lower = text.lower()
        scores = {}
        
        for intent, keywords in self.INTENT_PATTERNS.items():
            score = 0.0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1.0
            
            # Normalizar por número de keywords
            if keywords:
                scores[intent] = score / len(keywords)
        
        # Determinar intención principal
        if not scores or max(scores.values()) == 0:
            scores['general'] = 1.0
        
        return scores
    
    def get_primary_intent(self, text: str) -> str:
        """Obtiene la intención principal"""
        scores = self.classify_intent(text)
        return max(scores.items(), key=lambda x: x[1])[0]

class CapabilityDiscovery:
    """Discovery automático de capacidades MCP"""
    
    def __init__(self):
        self.server_configs = [
            MCPServerConfig(
                name="financial",
                path="src/mcp_server/server.py",
                description="Gestión financiera: transacciones, saldos, resúmenes",
                capabilities=["registrar_transaccion", "obtener_saldo", "obtener_transacciones"]
            ),
            MCPServerConfig(
                name="rag",
                path="src/mcp_server/rag_server.py", 
                description="Recuperación de información y consejos financieros",
                capabilities=["buscar_informacion", "expandir_contexto", "generar_respuesta_contextual"]
            )
        ]
        self.available_servers = {}
    
    async def discover_and_validate(self) -> Dict[str, MCPServerConfig]:
        """Descubre y valida servidores MCP disponibles"""
        print("🔍 Iniciando discovery de servidores MCP...")
        
        available = {}
        for config in self.server_configs:
            if os.path.exists(config.path):
                # Para la demo, asumimos que están disponibles si el archivo existe
                available[config.name] = config
                print(f"✅ Servidor encontrado: {config.name}")
            else:
                print(f"❌ Servidor no encontrado: {config.path}")
        
        self.available_servers = available
        return available

class RoutingEngine:
    """Motor de enrutamiento inteligente con fallbacks"""
    
    def __init__(self, discovery: CapabilityDiscovery):
        self.discovery = discovery
        self.intent_to_server = {
            'financial_query': ['financial'],
            'financial_action': ['financial'],
            'rag_query': ['rag', 'financial'],  # Fallback a financial si RAG no está disponible
            'general': ['rag', 'financial'],   # Intentar RAG primero, luego financial
            'help': None  # Manejado localmente
        }
    
    def route_intent(self, intent: str) -> Optional[str]:
        """
        Enruta una intención al servidor apropiado con fallbacks
        """
        server_preferences = self.intent_to_server.get(intent, ['financial'])
        
        if server_preferences is None:
            return None
        
        # Buscar el primer servidor disponible en orden de preferencia
        available_servers = self.discovery.available_servers
        for server_name in server_preferences:
            if server_name in available_servers:
                return server_name
        
        # Fallback final a financial si está disponible
        if 'financial' in available_servers:
            return 'financial'
        
        return None

class MemoryManager:
    """Manejo de memoria semántica y contexto conversacional"""
    
    def __init__(self):
        self.conversation_history = []
        self.context_cache = {}
        self.max_history = 10
    
    def add_interaction(self, user_input: str, agent_response: str, metadata: Dict[str, Any]):
        """Añade una interacción a la memoria"""
        interaction = {
            'timestamp': asyncio.get_event_loop().time(),
            'user_input': user_input,
            'agent_response': agent_response,
            'metadata': metadata
        }
        
        self.conversation_history.append(interaction)
        
        # Mantener solo las últimas N interacciones
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def get_context_summary(self) -> str:
        """Genera un resumen del contexto conversacional"""
        if not self.conversation_history:
            return "Primera interacción del usuario."
        
        recent_interactions = self.conversation_history[-3:]  # Últimas 3 interacciones
        summary = "Contexto reciente:\n"
        
        for i, interaction in enumerate(recent_interactions, 1):
            summary += f"{i}. Usuario: {interaction['user_input'][:100]}...\n"
            summary += f"   Respuesta: {interaction['agent_response'][:100]}...\n"
        
        return summary

class ConversationalAgent:
    """Agente conversacional con capacidades MCP reales"""
    
    def __init__(self):
        self.azure_client = None
        self.openai_model = None
        self.agent = None
        self.runner = None
        self.mcp_manager = None
        self.session_memory = []
        
    async def initialize(self):
        """Inicializa el agente y las conexiones MCP"""
        try:
            # Inicializar Azure OpenAI
            await self._setup_azure_openai()
            
            # Inicializar gestor MCP
            self.mcp_manager = MCPManager()
            
            # Conectar a servidores MCP
            await self._connect_mcp_servers()
            
            # Configurar agente con herramientas MCP
            await self._setup_agent_with_mcp()
            
            logger.info("✅ Agente conversacional inicializado con MCP real")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando agente: {e}")
            return False
    
    async def _connect_mcp_servers(self):
        """Conecta a todos los servidores MCP disponibles"""
        # Conectar a Tavily (búsqueda web)
        tavily_connected = await self.mcp_manager.connect_tavily_server()
        if tavily_connected:
            logger.info("🌐 Servidor Tavily MCP conectado")
        else:
            logger.warning("⚠️ No se pudo conectar al servidor Tavily MCP")
    
    async def _setup_agent_with_mcp(self):
        """Configura el agente con herramientas MCP disponibles"""
        # Obtener herramientas disponibles
        available_tools = await self.mcp_manager.get_available_tools()
        
        # Crear instrucciones del sistema que incluyan las capacidades MCP
        system_instructions = self._build_system_instructions(available_tools)
        
        # Crear agente
        self.agent = Agent(
            model=self.openai_model,
            instructions=system_instructions,
            name="EconomIAssist"
        )
        
        # Runner se usa como método estático, no se instancia
        self.runner = None

    def _build_system_instructions(self, available_tools: Dict[str, List[str]]) -> str:
        """Construye las instrucciones del sistema incluyendo capacidades MCP"""
        base_instructions = """Eres EconomIAssist, un asistente personal financiero inteligente.

CAPACIDADES PRINCIPALES:
1. 💰 Gestión financiera personal
2. 🧠 Consejos de educación financiera  
3. 📊 Análisis de gastos e ingresos
4. 🌐 Búsqueda de información financiera actualizada

PERSONALIDAD:
- Amigable y profesional
- Explicas conceptos financieros de manera simple
- Usas emojis para hacer la conversación más amena
- Siempre sugieres mejores prácticas financieras"""

        # Agregar capacidades MCP disponibles
        if available_tools:
            mcp_capabilities = "\n\nCAPACIDADES MCP DISPONIBLES:\n"
            for server, tools in available_tools.items():
                mcp_capabilities += f"🔧 {server.upper()}: {', '.join(tools)}\n"
            
            mcp_capabilities += """
CUANDO USAR MCP:
- Si el usuario pregunta sobre información financiera actual, usa búsqueda web
- Si necesitas datos actualizados sobre mercados, inversiones, etc.
- Para obtener noticias financieras recientes
- Para buscar información específica que no tienes en tu base de conocimiento

IMPORTANTE: Cuando uses herramientas MCP, explica al usuario qué estás haciendo."""
            
            base_instructions += mcp_capabilities
        
        return base_instructions

    async def _setup_azure_openai(self):
        """Configura Azure OpenAI"""
        try:
            azure_config = AzureOpenAIConfig()
            self.azure_client = azure_config.create_client()
            self.openai_model = azure_config.create_model()
            logger.info("✅ Azure OpenAI configurado correctamente")
        except Exception as e:
            logger.error(f"❌ Error configurando Azure OpenAI: {e}")
            raise

    async def process_query(self, user_input: str) -> str:
        """Alias para process_user_input para compatibilidad"""
        return await self.process_user_input(user_input)

    async def process_user_input(self, user_input: str) -> str:
        """
        Procesa la entrada del usuario y devuelve la respuesta del agente.
        
        Args:
            user_input (str): La consulta del usuario
            
        Returns:
            str: La respuesta del agente
        """
        try:
            print(f"🤖 Procesando consulta: {user_input}")
            
            # Ejecutar consulta usando OpenAI Agents SDK
            result = await Runner.run(self.agent, user_input)
            response = result.final_output
            
            print(f"✅ Respuesta generada ({len(response)} caracteres)")
            return response
            
        except Exception as e:
            error_msg = f"Error al procesar la consulta: {str(e)}"
            print(f"❌ {error_msg}")
            return f"Lo siento, ocurrió un error al procesar tu consulta: {str(e)}"
    
    async def _analyze_if_needs_web_search(self, user_input: str) -> bool:
        """Analiza si la consulta necesita búsqueda web"""
        web_keywords = [
            "actual", "actualizado", "reciente", "último", "últimas", "hoy", "2025",
            "mercado", "precio", "cotización", "noticias", "tendencias", 
            "inversión", "dólar", "bolsa", "acciones", "cripto"
        ]
        
        user_lower = user_input.lower()
        return any(keyword in user_lower for keyword in web_keywords)
    
    async def _extract_search_query(self, user_input: str) -> str:
        """Extrae una consulta de búsqueda optimizada del input del usuario"""
        # Simplificación: extraer términos clave financieros
        financial_terms = []
        
        keywords = ["dólar", "euro", "bitcoin", "acciones", "mercado", "inversión", 
                   "inflación", "tasas", "banco", "finanzas", "ahorro"]
        
        user_lower = user_input.lower()
        for keyword in keywords:
            if keyword in user_lower:
                financial_terms.append(keyword)
        
        if financial_terms:
            return f"{' '.join(financial_terms)} 2025 tendencias financieras"
        else:
            return f"{user_input} finanzas 2025"

    async def cleanup(self):
        """Limpia recursos al finalizar"""
        if self.mcp_manager:
            await self.mcp_manager.disconnect_all()
        logger.info("🧹 Recursos del agente limpiados")

async def main():
    """Función principal para ejecutar el agente conversacional"""
    print("🧠 EconomIAssist - Agente Conversacional Modular")
    print("=" * 70)
    print("🚀 Framework: OpenAI Agents SDK + Azure OpenAI GPT-4o-mini")
    print("🔧 Arquitectura: MCP (Model Context Protocol)")
    print("📋 Basado en: resumeProyect.txt")
    
    # Inicializar agente
    try:
        agent = ConversationalAgent()
        await agent.initialize()
    except Exception as e:
        print(f"❌ Error inicializando agente: {e}")
        return
    
    print("\n💬 ¡Listo para conversar! (Escribe 'salir' para terminar)")
    print("Ejemplo: '¿Cuál es mi saldo actual?' o 'ayuda'")
    
    while True:
        try:
            user_input = input("\n👤 Usuario: ").strip()
            
            if user_input.lower() in ['salir', 'exit', 'quit']:
                print("\n👋 ¡Hasta luego!")
                break
            
            if not user_input:
                continue
            
            # Procesar consulta con el agente
            print("🤔 Procesando...")
            response = await agent.process_query(user_input)
            print(f"\n🤖 **EconomIAssist:** {response}")
            
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())