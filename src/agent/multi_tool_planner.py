#!/usr/bin/env python3
"""
Multi-Tool Planning Agent para EconomIAssist
Permite planificación y ejecución de múltiples herramientas MCP en una sola consulta
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog

# Configurar logging
logger = structlog.get_logger(__name__)

class ExecutionStrategy(Enum):
    """Estrategias de ejecución de herramientas"""
    SEQUENTIAL = "sequential"  # Una tras otra
    PARALLEL = "parallel"     # En paralelo cuando sea posible
    CONDITIONAL = "conditional"  # Basado en resultados previos

@dataclass
class ToolPlan:
    """Plan de ejecución para una herramienta específica"""
    tool_name: str
    server_name: str
    parameters: Dict[str, Any]
    depends_on: List[str] = None  # Nombres de herramientas de las que depende
    priority: int = 1  # 1 = alta, 2 = media, 3 = baja
    required: bool = True  # Si es requerida para la respuesta final
    description: str = ""

@dataclass
class ExecutionResult:
    """Resultado de ejecución de una herramienta"""
    tool_name: str
    success: bool
    result: Any
    execution_time: float
    error: Optional[str] = None

class MultiToolPlanner:
    """
    Planificador inteligente que determina qué herramientas usar y en qué orden
    """
    
    def __init__(self, mcp_manager, azure_client, model_name):
        self.mcp_manager = mcp_manager
        self.azure_client = azure_client
        self.model_name = model_name
        
        # Definir capacidades y herramientas típicas
        self.tool_capabilities = {
            # Knowledge Base
            "knowledge_base_SearchMemory": {
                "capability": "memory_search",
                "triggers": ["mi", "mis", "recordar", "anterior", "dijiste", "mencioné"],
                "priority": 1,  # Siempre ejecutar primero
                "required_for": ["personal_queries", "context_dependent"]
            },
            "knowledge_base_CreateMemory": {
                "capability": "memory_storage", 
                "triggers": ["guardar", "recordar", "anotar", "soy", "me llamo"],
                "priority": 2,
                "required_for": ["information_storage"]
            },
            
            # Tavily - Web Search
            "tavily_search": {
                "capability": "current_data",
                "triggers": ["cotización", "precio", "actual", "hoy", "ahora", "último"],
                "priority": 2,
                "required_for": ["current_financial_data"]
            },
            
            # Calculator
            "calculator_calculate": {
                "capability": "calculations",
                "triggers": ["calcular", "cuánto", "%", "porcentaje", "suma", "resta"],
                "priority": 3,
                "required_for": ["mathematical_operations"]
            },
            
            # Google Calendar
            "google_calendar_create_event": {
                "capability": "calendar_management",
                "triggers": ["recordar", "alarma", "evento", "cita", "reunión"],
                "priority": 3,
                "required_for": ["scheduling"]
            },
            
            # Google Sheets
            "google_sheets_append_values": {
                "capability": "data_recording",
                "triggers": ["registrar", "anotar", "guardar", "historial"],
                "priority": 3,
                "required_for": ["data_storage"]
            }
        }
        
        logger.info("Multi-Tool Planner inicializado")
    
    async def analyze_query_and_plan(self, user_query: str, session_context: str = "") -> List[ToolPlan]:
        """
        Analiza la consulta del usuario y genera un plan de herramientas a ejecutar
        
        Args:
            user_query: Consulta del usuario
            session_context: Contexto de la sesión actual
            
        Returns:
            List[ToolPlan]: Lista ordenada de herramientas a ejecutar
        """
        logger.info("Analizando consulta para planning", query=user_query[:50])
        
        # Preparar prompt para el modelo de planificación
        planning_prompt = self._build_planning_prompt(user_query, session_context)
        
        try:
            # Llamar al modelo para obtener el plan
            response = await self.azure_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": planning_prompt}],
                temperature=0.1,  # Baja temperatura para consistencia
                max_tokens=1000
            )
            
            plan_json = response.choices[0].message.content.strip()
            
            # Intentar parsear el JSON del plan
            try:
                plan_data = json.loads(plan_json)
                tools_plan = self._parse_plan_json(plan_data)
                
                logger.info("Plan generado exitosamente", 
                           tools_count=len(tools_plan),
                           tools=[t.tool_name for t in tools_plan])
                
                return tools_plan
                
            except json.JSONDecodeError:
                logger.warning("Error parseando JSON del plan, usando heurísticas")
                return self._fallback_heuristic_planning(user_query)
                
        except Exception as e:
            logger.error("Error en planning", error=str(e))
            return self._fallback_heuristic_planning(user_query)
    
    def _build_planning_prompt(self, user_query: str, session_context: str) -> str:
        """Construye el prompt para el modelo de planificación"""
        
        available_tools = []
        for server_name, connection in self.mcp_manager.connections.items():
            for tool_name, tool in connection.tools.items():
                full_name = f"{server_name}_{tool_name}"
                available_tools.append({
                    "name": full_name,
                    "description": tool.description,
                    "server": server_name
                })
        
        tools_json = json.dumps(available_tools, indent=2)
        
        return f"""
Eres un planificador de herramientas para un asistente financiero argentino. 

CONSULTA DEL USUARIO: "{user_query}"

CONTEXTO DE SESIÓN:
{session_context if session_context else "No hay contexto previo"}

HERRAMIENTAS DISPONIBLES:
{tools_json}

REGLAS DE PLANIFICACIÓN:
1. Para consultas personales (mi, mis, recordar), SIEMPRE usar knowledge_base_SearchMemory PRIMERO
2. Para información nueva del usuario, usar knowledge_base_CreateMemory
3. Para datos actuales (cotizaciones, precios), usar tavily_search
4. Para cálculos matemáticos, usar calculator_calculate
5. Para recordatorios/eventos, usar google_calendar_create_event
6. Para registrar datos, usar google_sheets_append_values

GENERA UN PLAN EN JSON CON ESTE FORMATO:
{{
  "reasoning": "Breve explicación del plan",
  "execution_strategy": "sequential|parallel|conditional",
  "tools": [
    {{
      "tool_name": "nombre_servidor_herramienta",
      "server_name": "nombre_servidor",
      "parameters": {{"param1": "valor1"}},
      "priority": 1,
      "required": true,
      "description": "qué hace esta herramienta en este contexto",
      "depends_on": []
    }}
  ]
}}

IMPORTANTE: Responde SOLO con el JSON, sin texto adicional.
"""
    
    def _parse_plan_json(self, plan_data: Dict) -> List[ToolPlan]:
        """Parsea el JSON del plan y crea objetos ToolPlan"""
        tools_plan = []
        
        for tool_data in plan_data.get("tools", []):
            tool_plan = ToolPlan(
                tool_name=tool_data.get("tool_name", ""),
                server_name=tool_data.get("server_name", ""),
                parameters=tool_data.get("parameters", {}),
                depends_on=tool_data.get("depends_on", []),
                priority=tool_data.get("priority", 2),
                required=tool_data.get("required", True),
                description=tool_data.get("description", "")
            )
            tools_plan.append(tool_plan)
        
        # Ordenar por prioridad (1 = más alta)
        tools_plan.sort(key=lambda x: x.priority)
        
        return tools_plan
    
    def _fallback_heuristic_planning(self, user_query: str) -> List[ToolPlan]:
        """Planificación heurística simple cuando falla el modelo"""
        logger.info("Usando planificación heurística")
        
        query_lower = user_query.lower()
        tools_plan = []
        
        # 1. ¿Es consulta personal? -> Buscar en memoria primero
        if any(word in query_lower for word in ["mi", "mis", "recordar", "dijiste", "anterior"]):
            tools_plan.append(ToolPlan(
                tool_name="knowledge_base_SearchMemory",
                server_name="knowledge_base",
                parameters={
                    "phrases": [query_lower],
                    "topics": ["Perfil Personal", "Finanzas"],
                    "importance": 0.8
                },
                priority=1,
                description="Buscar información personal en memoria"
            ))
        
        # 2. ¿Necesita datos actuales?
        if any(word in query_lower for word in ["cotización", "precio", "actual", "hoy", "dólar"]):
            tools_plan.append(ToolPlan(
                tool_name="tavily_search",
                server_name="tavily",
                parameters={
                    "query": f"{user_query} Argentina"
                },
                priority=2,
                description="Buscar información financiera actual"
            ))
        
        # 3. ¿Requiere cálculos?
        if any(word in query_lower for word in ["calcular", "cuánto", "%", "porcentaje"]):
            # Extraer expresión matemática básica
            tools_plan.append(ToolPlan(
                tool_name="calculator_calculate",
                server_name="calculator",
                parameters={
                    "expression": "100 + 200"  # Placeholder, se refinará
                },
                priority=3,
                description="Realizar cálculos matemáticos"
            ))
        
        return tools_plan

class MultiToolExecutor:
    """
    Ejecutor que maneja la ejecución de múltiples herramientas según el plan
    """
    
    def __init__(self, mcp_manager):
        self.mcp_manager = mcp_manager
        logger.info("Multi-Tool Executor inicializado")
    
    async def execute_plan(self, tools_plan: List[ToolPlan]) -> Dict[str, ExecutionResult]:
        """
        Ejecuta el plan de herramientas y retorna los resultados
        
        Args:
            tools_plan: Lista de herramientas a ejecutar
            
        Returns:
            Dict[str, ExecutionResult]: Resultados indexados por nombre de herramienta
        """
        logger.info("Ejecutando plan multi-herramienta", tools_count=len(tools_plan))
        
        results = {}
        
        # Ejecutar herramientas en orden de prioridad
        for tool_plan in tools_plan:
            try:
                start_time = asyncio.get_event_loop().time()
                
                logger.info("Ejecutando herramienta", 
                           tool=tool_plan.tool_name,
                           params=tool_plan.parameters)
                
                # Verificar dependencias
                if tool_plan.depends_on:
                    missing_deps = [dep for dep in tool_plan.depends_on if dep not in results]
                    if missing_deps:
                        logger.warning("Dependencias faltantes", 
                                     tool=tool_plan.tool_name,
                                     missing=missing_deps)
                        continue
                
                # Ejecutar herramienta
                result = await self.mcp_manager.call_tool_by_function_name(
                    tool_plan.tool_name, 
                    tool_plan.parameters
                )
                
                execution_time = asyncio.get_event_loop().time() - start_time
                
                results[tool_plan.tool_name] = ExecutionResult(
                    tool_name=tool_plan.tool_name,
                    success=True,
                    result=result,
                    execution_time=execution_time
                )
                
                logger.info("Herramienta ejecutada exitosamente",
                           tool=tool_plan.tool_name,
                           execution_time=execution_time)
                
            except Exception as e:
                execution_time = asyncio.get_event_loop().time() - start_time
                
                results[tool_plan.tool_name] = ExecutionResult(
                    tool_name=tool_plan.tool_name,
                    success=False,
                    result=None,
                    execution_time=execution_time,
                    error=str(e)
                )
                
                logger.error("Error ejecutando herramienta",
                           tool=tool_plan.tool_name,
                           error=str(e))
                
                # Si la herramienta es requerida, considerar si continuar
                if tool_plan.required:
                    logger.warning("Herramienta requerida falló", tool=tool_plan.tool_name)
        
        return results

class ResponseSynthesizer:
    """
    Sintetizador que combina resultados de múltiples herramientas en una respuesta coherente
    """
    
    def __init__(self, azure_client, model_name):
        self.azure_client = azure_client
        self.model_name = model_name
        logger.info("Response Synthesizer inicializado")
    
    async def synthesize_response(
        self, 
        user_query: str, 
        execution_results: Dict[str, ExecutionResult],
        tools_plan: List[ToolPlan]
    ) -> str:
        """
        Sintetiza una respuesta coherente basada en los resultados de múltiples herramientas
        
        Args:
            user_query: Consulta original del usuario
            execution_results: Resultados de ejecución de herramientas
            tools_plan: Plan original de herramientas
            
        Returns:
            str: Respuesta sintetizada
        """
        logger.info("Sintetizando respuesta", tools_executed=len(execution_results))
        
        # Preparar contexto de resultados
        results_context = self._build_results_context(execution_results, tools_plan)
        
        synthesis_prompt = f"""
Eres EconomIAssist, un asistente financiero argentino. Debes sintetizar una respuesta coherente basada en los resultados de múltiples herramientas.

CONSULTA ORIGINAL: "{user_query}"

RESULTADOS DE HERRAMIENTAS:
{results_context}

INSTRUCCIONES:
1. Combina los resultados de manera natural y coherente
2. Prioriza información personal (memoria) sobre información general
3. Incluye datos actuales cuando estén disponibles
4. Si hay cálculos, muestra el proceso y resultado
5. Responde en español argentino coloquial
6. Si alguna herramienta falló, no menciones el error técnico

GENERA UNA RESPUESTA NATURAL que responda a la consulta del usuario usando TODOS los resultados relevantes disponibles.
"""
        
        try:
            response = await self.azure_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": synthesis_prompt}],
                temperature=0.7,
                max_tokens=1500
            )
            
            synthesized_response = response.choices[0].message.content.strip()
            
            logger.info("Respuesta sintetizada exitosamente", 
                       response_length=len(synthesized_response))
            
            return synthesized_response
            
        except Exception as e:
            logger.error("Error en síntesis", error=str(e))
            return self._fallback_synthesis(user_query, execution_results)
    
    def _build_results_context(self, results: Dict[str, ExecutionResult], tools_plan: List[ToolPlan]) -> str:
        """Construye el contexto de resultados para la síntesis"""
        context_parts = []
        
        for tool_plan in tools_plan:
            tool_name = tool_plan.tool_name
            result = results.get(tool_name)
            
            if result and result.success:
                context_parts.append(f"""
HERRAMIENTA: {tool_name}
PROPÓSITO: {tool_plan.description}
RESULTADO: {json.dumps(result.result, indent=2, ensure_ascii=False)}
ÉXITO: ✅
""")
            elif result:
                context_parts.append(f"""
HERRAMIENTA: {tool_name}
PROPÓSITO: {tool_plan.description}
RESULTADO: Error - {result.error}
ÉXITO: ❌
""")
        
        return "\n".join(context_parts)
    
    def _fallback_synthesis(self, user_query: str, results: Dict[str, ExecutionResult]) -> str:
        """Síntesis de fallback simple"""
        successful_results = [r for r in results.values() if r.success]
        
        if not successful_results:
            return "Lo siento, tuve problemas procesando tu consulta. ¿Podrías intentar de nuevo?"
        
        response_parts = [f"Basándome en tu consulta '{user_query}', puedo decirte:"]
        
        for result in successful_results:
            if result.result:
                response_parts.append(f"- {result.result}")
        
        return "\n".join(response_parts)