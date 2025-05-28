#!/usr/bin/env python3
"""
Agente Conversacional Modular - OpenAI Azure SDK con MCP Real
Implementación completa con conexión real a servidores MCP externos
"""

import asyncio
import os
import json
import warnings
from typing import Dict, List, Any
from dataclasses import dataclass
import structlog
from dotenv import load_dotenv
from datetime import datetime  # Para incluir fecha actual

# Suprimir warnings de tracing del OpenAI SDK
warnings.filterwarnings("ignore")
os.environ["OPENAI_LOG_LEVEL"] = "ERROR"

# Cargar variables de entorno
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(env_path, override=True)

# OpenAI Azure SDK imports
from openai import AsyncAzureOpenAI

# Importar cliente MCP real
try:
    from .mcp_client import MCPManager
    from .intentParser import IntentParser, IntentResponse  # import local de intentParser.py
except ImportError:
    # Cuando se ejecuta directamente, usar importación absoluta
    from mcp_client import MCPManager
    from intentParser import IntentParser, IntentResponse  # import local de intentParser.py

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

class MemoryManager:
    """Manejo de memoria semántica y contexto conversacional"""
    def __init__(self):
        self.conversation_history = []
        self.context_cache = {}
        self.max_history = 5  # Máximo de interacciones a mantener en memoria
    
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
        self.mcp_manager = None
        self.session_memory = []
        # Integración de parser de intenciones y memoria conversacional
        self.intent_parser = IntentParser()
        self.memory_manager = MemoryManager()


    async def initialize(self):
        """Inicializa el agente y las conexiones MCP"""
        try:
            # Inicializar Azure OpenAI
            await self._setup_azure_openai()
            # Inicializar gestor MCP
            self.mcp_manager = MCPManager()
            # Conectar a servidores MCP
            await self._connect_mcp_servers()
            # Configurar herramientas MCP
            await self._setup_mcp_tools()
            logger.info("✅ Agente conversacional inicializado con MCP")
            return True
        except Exception as e:
            logger.error(f"❌ Error inicializando agente: {e}")
            return False
    
    
    def _build_system_instructions(self, available_tools: Dict[str, List[str]]) -> str:
        """Crea instrucciones de sistema describiendo el agente y sus herramientas MCP"""
        date_str = datetime.now().strftime("%d de %B de %Y")
        instr = [
            f"Hoy es {date_str}.",
            "Eres EconomIAssist, un asistente financiero personal.",
            "Dispones de las siguientes herramientas MCP para tareas especializadas:"
        ]
        for srv, tools in available_tools.items():
            instr.append(f"- Servidor '{srv}': herramientas {', '.join(tools)}.")
        instr.append("Cuando recibas una llamada de función, invoca la herramienta adecuada con los parámetros proporcionados.")
        return "\n".join(instr)
    
    
    async def _connect_mcp_servers(self):
        """Conecta a todos los servidores MCP disponibles usando auto-discovery"""
        # Usar el nuevo sistema de auto-conexión
        connection_results = await self.mcp_manager.auto_connect_servers()
        
        connected_count = sum(1 for success in connection_results.values() if success)
        total_count = len(connection_results)
        
        if connected_count > 0:
            logger.info(f"🌐 {connected_count}/{total_count} servidores MCP conectados")
            
            # Mostrar estadísticas detalladas
            stats = self.mcp_manager.get_connection_stats()
            logger.info(f"📊 Capacidades disponibles: {list(stats['servers_by_capability'].keys())}")
        else:
            logger.warning("⚠️ No se pudieron conectar servidores MCP")
    
    
    async def _setup_mcp_tools(self):
        """Configura las herramientas MCP disponibles"""
        available_tools = await self.mcp_manager.get_available_tools()
        self.system_instructions = self._build_system_instructions(available_tools)
        self.mcp_functions = []
        for srv, conn in self.mcp_manager.connections.items():
            for tool in conn.tools.values():
                self.mcp_functions.append({
                    "name": f"{srv}_{tool.name}",
                    "description": tool.description,
                    "parameters": tool.input_schema
                })
    
    
    async def _setup_azure_openai(self):
        """Configura Azure OpenAI"""
        try:
            azure_config = AzureOpenAIConfig()
            self.azure_client = azure_config.create_client()
            self.openai_model = azure_config.deployment_name
            logger.info("✅ Azure OpenAI configurado correctamente")
        except Exception as e:
            logger.error(f"❌ Error configurando Azure OpenAI: {e}")
            raise
    
    
    async def _call_openai_with_mcp(self, user_input: str) -> str:
        """Invoca Azure OpenAI incluyendo la ventana de contexto conversacional, las funciones MCP y maneja llamadas de función"""
        # Obtener resumen de contexto conversacional
        context_summary = self.memory_manager.get_context_summary()
        
        # Construir mensajes con instrucciones del sistema, contexto y entrada del usuario
        messages = [
            {"role": "system", "content": self.system_instructions},
            {"role": "system", "content": context_summary},
            {"role": "user", "content": user_input}
        ]
        
        # Solo incluir funciones si hay herramientas MCP disponibles
        if self.mcp_functions:
            resp = await self.azure_client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                functions=self.mcp_functions,
                function_call="auto"
            )
            
            msg = resp.choices[0].message
            if msg.function_call:
                fname = msg.function_call.name
                params = json.loads(msg.function_call.arguments)
                srv, tname = fname.split("_", 1)
                result = await self.mcp_manager.connections[srv].call_tool(tname, params)
                messages.append({"role": "assistant", "content": None, "function_call": msg.function_call.to_dict()})
                messages.append({"role": "function", "name": fname, "content": json.dumps(result)})
                follow = await self.azure_client.chat.completions.create(
                    model=self.openai_model,
                    messages=messages
                )
                return follow.choices[0].message.content
            return msg.content
        else:
            # Sin herramientas MCP, usar conversación normal
            resp = await self.azure_client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            return resp.choices[0].message.content
    
    
    async def process_query(self, user_input: str) -> str:
        return await self.process_user_input(user_input)


    async def process_user_input(self, user_input: str) -> str:
        parsed_intents = self.intent_parser.receive_message(user_input)
        logger.info(f"🔍 Intenciones detectadas: {parsed_intents}")
        try:
            print(f"🤖 Procesando consulta: {user_input}")
            response = await self._call_openai_with_mcp(user_input)
            self.memory_manager.add_interaction(user_input, response, {"intents": parsed_intents})
            print(f"✅ Respuesta generada ({len(response)} caracteres)")
            return response
        except Exception as e:
            error_msg = f"Error al procesar la consulta: {str(e)}"
            print(f"❌ {error_msg}")
            return f"Lo siento, ocurrió un error al procesar tu consulta: {str(e)}"
    

    async def cleanup(self):
        if self.mcp_manager:
            await self.mcp_manager.disconnect_all()
        logger.info("🧹 Recursos del agente limpiados")
    

    def get_short_term_memory(self) -> str:
        """Devuelve el resumen de la memoria de corto plazo (short term memory) de la conversación."""
        return self.memory_manager.get_context_summary()
    

    def add_to_short_term_memory(self, user_input: str, agent_response: str, metadata: Dict[str, Any] = None):
        """Agrega una interacción a la memoria de corto plazo."""
        if metadata is None:
            metadata = {}
        self.memory_manager.add_interaction(user_input, agent_response, metadata)


async def main():
    print("🧠 EconomIAssist - Agente Conversacional Modular")
    print("=" * 70)
    print("🚀 Framework: Azure OpenAI GPT-4o-mini")
    print("🔧 Arquitectura: MCP (Model Context Protocol)")
    print("📋 Basado en: resumeProyect.txt")
    try:
        agent = ConversationalAgent()
        initialized = await agent.initialize()
        if not initialized:
            print("❌ No se pudo inicializar el agente. Saliendo.")
            return
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