#!/usr/bin/env python3
"""
Agente Conversacional Modular - OpenAI Azure SDK con MCP Real
Implementación completa con conexión real a servidores MCP externos
"""

import asyncio
import os
import json
import warnings
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import structlog
from dotenv import load_dotenv
from datetime import datetime  # Para incluir fecha actual
import time  # Para medir tiempos de ejecución

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
    from .rag_module import query_rag  # Import RAG module
    # Importar loggers
    from ..utils.agent_logger import AgentLogger
    from ..utils.mcp_logger import MCPLogger
    from ..utils.intent_logger import IntentLogger
except ImportError:
    # Cuando se ejecuta directamente, usar importación absoluta
    from mcp_client import MCPManager
    from intentParser import IntentParser, IntentResponse
    from rag_module import query_rag  # Import RAG module
    
    # Importar loggers con ruta absoluta cuando se ejecuta directamente
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from utils.agent_logger import AgentLogger
    from utils.mcp_logger import MCPLogger
    from utils.intent_logger import IntentLogger

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
    """Agente conversacional con capacidades MCP reales y RAG"""
    def __init__(self):
        self.azure_client = None
        self.openai_model = None
        self.mcp_manager = None
        # Memoria temporal para contexto de sesión actual (no persistente)
        self.current_session_context = []
        # Solo parser de intenciones
        self.intent_parser = IntentParser()
        # RAG availability flag
        self.rag_available = False
        
        # Add agent logger
        self.agent_logger = AgentLogger(agent_id="main_agent")
        self.agent_logger.info("Agent instance created")


    async def initialize(self):
        """Inicializa el agente y las conexiones MCP"""
        components_status = {
            "azure_openai": False,
            "mcp_manager": False,
            "mcp_servers": False,
            "mcp_tools": False,
            "rag_module": False
        }
        
        start_time = time.time()
        
        try:
            # Inicializar Azure OpenAI
            await self._setup_azure_openai()
            components_status["azure_openai"] = True
            
            # Inicializar gestor MCP
            self.mcp_manager = MCPManager()
            components_status["mcp_manager"] = True
            
            # Conectar a servidores MCP
            await self._connect_mcp_servers()
            components_status["mcp_servers"] = True
            
            # Configurar herramientas MCP
            await self._setup_mcp_tools()
            components_status["mcp_tools"] = True
            
            # Check RAG availability
            self._check_rag_availability()
            components_status["rag_module"] = self.rag_available
            
            print("✅ Agente conversacional inicializado")
            
            # Log successful initialization
            self.agent_logger.log_initialization(success=True, components=components_status)
            self.agent_logger.info("Agent initialization completed", 
                                  initialization_time=time.time() - start_time)
            
            return True
        except Exception as e:
            # Log initialization error
            self.agent_logger.log_error(
                error_message=f"Error durante inicialización: {str(e)}",
                error_type="initialization_error",
                details={"components_status": components_status}
            )
            
            print(f"❌ Error inicializando agente: {e}")
            return False
    
    
    def _load_system_instructions(self) -> str:
        """Carga las instrucciones del sistema desde archivo externo"""
        instructions_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'system_instructions.txt')
        
        try:
            with open(instructions_path, 'r', encoding='utf-8') as f:
                instructions_template = f.read()
            return instructions_template
        except FileNotFoundError:
            logger.warning(f"⚠️ Archivo de instrucciones no encontrado: {instructions_path}")
            # Fallback a instrucciones básicas
            return "Eres EconomIAssist, un asistente financiero personal. {tools_description}"
        except Exception as e:
            logger.error(f"❌ Error cargando instrucciones: {e}")
            return "Eres EconomIAssist, un asistente financiero personal. {tools_description}"
    
    def _build_system_instructions(self, available_tools: Dict[str, List[str]]) -> str:
        """Crea instrucciones de sistema usando template externo y herramientas MCP"""
        date_str = datetime.now().strftime("%d de %B de %Y")
        
        # Cargar template de instrucciones
        instructions_template = self._load_system_instructions()
        
        # Construir descripción de herramientas de forma genérica
        tools_description = []
        
        for srv, tools in available_tools.items():
            tools_description.append(f"- Servidor '{srv}': {', '.join(tools)}")
        
        tools_text = "\n".join(tools_description)
        
        # Reemplazar placeholders en el template
        final_instructions = instructions_template.format(
            tools_description=tools_text
        )
        
        # Agregar fecha al inicio
        return f"Hoy es {date_str}.\n\n{final_instructions}"
    
    
    async def _connect_mcp_servers(self):
        """Conecta a todos los servidores MCP disponibles usando auto-discovery"""
        start_time = time.time()
        
        # Usar el nuevo sistema de auto-conexión
        connection_results = await self.mcp_manager.auto_connect_servers()
        
        connected_count = sum(1 for success in connection_results.values() if success)
        total_count = len(connection_results)
        
        # Log MCP server connections
        self.agent_logger.info("MCP servers connection completed", 
                              connected=f"{connected_count}/{total_count}",
                              connection_time=time.time() - start_time)
        
        if connected_count > 0:
            print(f"🌐 {connected_count}/{total_count} servidores MCP conectados")
        else:
            self.agent_logger.warning("No MCP servers could be connected")
            print("⚠️ No se pudieron conectar servidores MCP")
    
    
    async def _setup_mcp_tools(self):
        """Configura las herramientas MCP disponibles"""
        start_time = time.time()
        
        available_tools = await self.mcp_manager.get_available_tools()
        self.system_instructions = self._build_system_instructions(available_tools)
        self.mcp_functions = []
        
        tool_count = 0
        servers_tools = {}
        
        for srv, conn in self.mcp_manager.connections.items():
            servers_tools[srv] = len(conn.tools)
            for tool in conn.tools.values():
                function_def = {
                    "name": f"{srv}_{tool.name}",
                    "description": tool.description,
                    "parameters": tool.input_schema or {"type": "object", "properties": {}}
                }
                self.mcp_functions.append(function_def)
                tool_count += 1
        
        # Log MCP tools initialization
        self.agent_logger.log_mcp_tools_initialized(
            tool_count=tool_count,
            servers=servers_tools
        )
        
        self.agent_logger.info("MCP tools setup completed", 
                          tool_count=tool_count,
                          servers_count=len(servers_tools),
                          setup_time=time.time() - start_time)
        
        print(f"🔧 {tool_count} herramientas MCP disponibles")
    
    async def _setup_azure_openai(self):
        """Configura Azure OpenAI"""
        start_time = time.time()
        
        try:
            azure_config = AzureOpenAIConfig()
            self.azure_client = azure_config.create_client()
            self.openai_model = azure_config.deployment_name
            
            # Log successful Azure OpenAI setup
            setup_time = time.time() - start_time
            safe_config = {
                "api_base": azure_config.api_base,
                "api_version": azure_config.api_version,
                "deployment": azure_config.deployment_name,
                "api_key": "[REDACTED]"
            }
            
            self.agent_logger.info("Azure OpenAI configured successfully", 
                                  model=self.openai_model,
                                  setup_time=setup_time,
                                  config=safe_config)
            
        except Exception as e:
            # Log error in Azure OpenAI setup
            self.agent_logger.error("Azure OpenAI configuration failed", 
                                   error=str(e),
                                   error_type=type(e).__name__,
                                   setup_time=time.time() - start_time)
            
            print(f"❌ Error configurando Azure OpenAI: {e}")
            raise
    
    def _check_rag_availability(self):
        """Check if RAG module and vector database are available"""
        try:
            # Try to import query_rag and check if chroma DB exists
            chroma_path = os.path.join(os.path.dirname(__file__), '..', '..', 'chroma_db')
            if os.path.exists(chroma_path):
                # Try a simple test query to verify RAG is working
                test_result = query_rag("test", k=1, relevance_threshold=0.1)
                self.rag_available = True
                print("✅ RAG module available and working")
            else:
                self.rag_available = False
                print("❌ RAG database not found")
        except Exception as e:
            self.rag_available = False
            print(f"❌ RAG module not available: {e}")
    
    def _should_use_rag(self, intent_type: str) -> bool:
        """Determine if a query should use RAG based on intent type"""
        rag_intent_types = {
            "EDUCACION_FINANCIERA", 
            "CONSULTA_GENERAL", 
            "ASESORAMIENTO",
            "define",  # From intent parser output
            "query"   # From intent parser output
        }
        return intent_type in rag_intent_types and self.rag_available
    
    def _get_rag_context(self, user_input: str) -> str:
        """Get RAG context for theoretical questions"""
        try:
            context = query_rag(user_input, k=3, relevance_threshold=0.3)
            if context:
                return f"CONTEXTO RELEVANTE DE LA BASE DE CONOCIMIENTO:\n{context}\n\n"
            return ""
        except Exception as e:
            logger.warning(f"Error getting RAG context: {e}")
            return ""
    
    async def _call_openai_with_mcp(self, user_input: str, intent_type: str = None) -> str:
        """Invoca Azure OpenAI incluyendo las funciones MCP y maneja llamadas de función"""
        start_time = time.time()
        
        # Log user input
        self.agent_logger.log_user_input(user_input)
        
        # Construir contexto de sesión
        session_context = self._build_session_context_for_llm()
        
        # Get RAG context if this is a theoretical question
        rag_context = ""
        if intent_type and self._should_use_rag(intent_type):
            rag_context = self._get_rag_context(user_input)
            if rag_context:
                print(f"📚 Using RAG context for {intent_type} query")
        
        # Construir instrucciones del sistema con contexto de sesión y RAG
        system_content = self.system_instructions
        if session_context:
            system_content = f"{self.system_instructions}\n\n{session_context}"
        if rag_context:
            # For theoretical questions, add specific instructions to prioritize RAG content
            rag_instructions = (
                "\n\nIMPORTANTE: Para preguntas teóricas y definiciones, DEBES usar principalmente el contexto "
                "de la base de conocimiento proporcionado arriba. Si necesitas información adicional, "
                "puedes complementar con búsquedas web, pero SIEMPRE prioriza y menciona la información "
                "de la base de conocimiento primero.\n"
            )
            system_content = f"{system_content}\n\n{rag_context}{rag_instructions}"
        
        # Construir mensajes con instrucciones del sistema y entrada del usuario
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_input}
        ]
        
        # Solo incluir funciones si hay herramientas MCP disponibles
        if self.mcp_functions:
            # Log OpenAI API call
            self.agent_logger.log_openai_call(model=self.openai_model)
            
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
                
                # DEBUG: Mostrar qué función se está intentando llamar
                print(f"🔧 Intentando llamar función MCP: {fname}")
                print(f"   Parámetros: {params}")
                
                # Log function call attempt
                self.agent_logger.info("Function call detected", 
                                      function=fname,
                                      args=params)
                
                try:
                    func_start_time = time.time()
                    
                    # Usar método agnóstico del MCPManager
                    result = await self.mcp_manager.call_tool_by_function_name(fname, params)
                    print(f"✅ Función MCP exitosa: {fname}")
                    print(f"   Resultado: {result}")
                    
                    # Log successful function call
                    func_execution_time = time.time() - func_start_time
                    self.agent_logger.log_function_call(
                        function_name=fname,
                        success=True,
                        execution_time=func_execution_time
                    )
                    
                except Exception as e:
                    # Log function call error
                    self.agent_logger.log_function_call(
                        function_name=fname,
                        success=False,
                        execution_time=time.time() - func_start_time
                    )
                    
                    self.agent_logger.error("Function execution error", 
                                          function=fname,
                                          error=str(e),
                                          error_type=type(e).__name__)
                    
                    print(f"❌ Error en función MCP {fname}: {e}")
                    # Continuar con el flujo normal en caso de error
                    return f"Lo siento, hubo un problema al procesar tu solicitud: {str(e)}"
                
                messages.append({"role": "assistant", "content": None, "function_call": msg.function_call.to_dict()})
                messages.append({"role": "function", "name": fname, "content": json.dumps(result)})
                
                # Log second OpenAI call
                self.agent_logger.log_openai_call(model=self.openai_model)
                
                follow = await self.azure_client.chat.completions.create(
                    model=self.openai_model,
                    messages=messages
                )
                response = follow.choices[0].message.content
            else:
                response = msg.content
        else:
            # Sin herramientas MCP, usar conversación normal
            # Log OpenAI API call
            self.agent_logger.log_openai_call(model=self.openai_model)
            
            resp = await self.azure_client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            response = resp.choices[0].message.content
        
        # Log agent response
        self.agent_logger.log_agent_response(response)
        
        # Log total processing time
        total_time = time.time() - start_time
        self.agent_logger.info("Response generated successfully", 
                              total_processing_time=total_time,
                              response_length=len(response))
        
        return response
    
    
    async def process_query(self, user_input: str) -> str:
        # Check if the input matches one of the exit codes
        if user_input.lower() in ['salir', 'exit', 'quit']:
            evaluation_form_url = os.getenv("EVALUATION_FORM_URL", "No form URL found")
            return f"👋 ¡Hasta luego! Por favor, evalúa nuestra aplicación aquí: {evaluation_form_url}"

        return await self.process_user_input(user_input)


    async def process_user_input(self, user_input: str) -> str:
        parsed_intents = self.intent_parser.receive_message(user_input)
        logger.info(f"🔍 Intenciones detectadas: {parsed_intents}")

        responses = {}
        for intent in parsed_intents:
            try:
                if intent.depends_on:
                    dependency_result = responses.get(intent.depends_on)
                    if not dependency_result:
                        raise ValueError(f"Dependencia no satisfecha: {intent.depends_on}")

                    # Modify the intent value to include the dependency result
                    intent.value = f"{intent.value} usando resultado: {dependency_result}"

                # Pass the intent type to the OpenAI call for RAG decision
                response = await self._call_openai_with_mcp(intent.value, intent.intent)
                responses[intent.intent] = response

                print(f"✅ Respuesta generada para intención '{intent.intent}': {response}")
                
                # Add to session context for each processed intent
                self._add_to_session_context(intent.value, response)

            except Exception as e:
                error_msg = f"Error al procesar la intención '{intent.intent}': {str(e)}"
                self.agent_logger.log_error(
                    error_message=error_msg,
                    error_type=type(e).__name__,
                    details={"intent": intent.dict()}
                )
                responses[intent.intent] = f"❌ {error_msg}"

        # Combine all responses into a single string
        return "\n".join(responses.values())
    

    def _add_to_session_context(self, user_input: str, assistant_response: str):
        """Agrega la interacción a la memoria temporal de sesión"""
        interaction = {
            "user": user_input,
            "assistant": assistant_response,
            "timestamp": datetime.now().isoformat()
        }
        
        self.current_session_context.append(interaction)
        
        # Mantener solo las últimas 5 interacciones para no saturar el contexto
        if len(self.current_session_context) > 5:
            self.current_session_context = self.current_session_context[-5:]
    
    def _build_session_context_for_llm(self) -> str:
        """Construye el contexto de sesión para incluir en el prompt"""
        if not self.current_session_context:
            return ""
        
        context_parts = ["CONTEXTO DE LA CONVERSACIÓN ACTUAL:"]
        
        # Tomar las últimas 5 interacciones completas
        recent_interactions = self.current_session_context[-5:]
        
        for i, interaction in enumerate(recent_interactions, 1):
            context_parts.append(f"{i}. Usuario: {interaction['user']}")
            context_parts.append(f"   Asistente: {interaction['assistant']}")
        
        context_parts.append("--- FIN DEL CONTEXTO ---")
        context_parts.append("IMPORTANTE: Cuando el usuario se refiera a mensajes anteriores, usa este contexto para responder correctamente.")
        return "\n".join(context_parts)
    

    async def cleanup(self):
        if self.mcp_manager:
            await self.mcp_manager.disconnect_all()
        
        # Log cleanup
        self.agent_logger.log_cleanup(success=True)
        
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
            # if user_input.lower() in ['salir', 'exit', 'quit']:
            #     print("\n👋 ¡Hasta luego!")
            #     break
            if not user_input:
                continue
            print("🤔 Procesando...")
            response = await agent.process_query(user_input)
            print(f"\n🤖 **EconomIAssist:** {response}")
            if response.startswith("👋 ¡Hasta luego!"):
                break
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())