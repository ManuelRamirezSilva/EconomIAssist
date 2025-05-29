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

class ConversationalAgent:
    """Agente conversacional con capacidades MCP reales"""
    def __init__(self):
        self.azure_client = None
        self.openai_model = None
        self.mcp_manager = None
        self.session_memory = []
        # Solo parser de intenciones - sin MemoryManager
        self.intent_parser = IntentParser()


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
    
    async def _setup_mcp_tools(self):
        """Configura las herramientas MCP disponibles"""
        available_tools = await self.mcp_manager.get_available_tools()
        self.system_instructions = self._build_system_instructions(available_tools)
        self.mcp_functions = []
        
        for srv, conn in self.mcp_manager.connections.items():
            for tool in conn.tools.values():
                function_def = {
                    "name": f"{srv}_{tool.name}",
                    "description": tool.description,
                    "parameters": tool.input_schema or {"type": "object", "properties": {}}
                }
                self.mcp_functions.append(function_def)
                logger.info(f"📝 Función MCP registrada: {function_def['name']} - {function_def['description'][:50]}...")
        
        logger.info(f"🔧 Total funciones MCP disponibles: {len(self.mcp_functions)}")
        logger.debug(f"📋 Instrucciones del sistema:\n{self.system_instructions}")
    
    async def _call_openai_with_mcp(self, user_input: str) -> str:
        """Invoca Azure OpenAI incluyendo las funciones MCP y maneja llamadas de función"""
        messages = [
            {"role": "system", "content": self.system_instructions},
            {"role": "user", "content": user_input}
        ]
        
        # Agregar memoria de sesión temporal
        for memory in self.session_memory[-5:]:
            messages.insert(-1, {"role": "user", "content": memory["user"]})
            messages.insert(-1, {"role": "assistant", "content": memory["assistant"]})
        
        if self.mcp_functions:
            resp = await self.azure_client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                functions=self.mcp_functions,
                function_call="auto",
                temperature=0.1,
                max_tokens=1500
            )
            
            msg = resp.choices[0].message
            if msg.function_call:
                fname = msg.function_call.name
                params = json.loads(msg.function_call.arguments)
                
                logger.info(f"🔧 Intentando llamar función MCP: {fname}")
                logger.debug(f"   Parámetros: {params}")
                
                try:
                    result = await self.mcp_manager.call_tool_by_function_name(fname, params)
                    logger.info(f"✅ Función MCP exitosa: {fname}")
                    logger.debug(f"   Resultado: {result}")
                except Exception as e:
                    logger.error(f"❌ Error en función MCP {fname}: {e}")
                    return f"Lo siento, hubo un problema al procesar tu solicitud: {str(e)}"
                
                messages.append({"role": "assistant", "content": None, "function_call": msg.function_call.to_dict()})
                messages.append({"role": "function", "name": fname, "content": json.dumps(result)})
                follow = await self.azure_client.chat.completions.create(
                    model=self.openai_model,
                    messages=messages,
                    temperature=0.7
                )
                response = follow.choices[0].message.content
            else:
                response = msg.content
        else:
            resp = await self.azure_client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            response = resp.choices[0].message.content
        
        self.session_memory.append({
            "user": user_input,
            "assistant": response
        })
        
        return response
    
    
    async def process_query(self, user_input: str) -> str:
        return await self.process_user_input(user_input)


    async def process_user_input(self, user_input: str) -> str:
        parsed_intents = self.intent_parser.receive_message(user_input)
        logger.info(f"🔍 Intenciones detectadas: {parsed_intents}")
        try:
            print(f"🤖 Procesando consulta: {user_input}")
            response = await self._call_openai_with_mcp(user_input)
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