#!/usr/bin/env python3
"""
Servidor MCP RAG - Recuperación de información y expansión de contexto
Componente especializado del sistema modular EconomIAssist
"""

from mcp.server.fastmcp import FastMCP
import json
import sys
import os
from typing import List, Dict, Any
import hashlib

# Agregar utils al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.env_loader import load_environment_variables

# Cargar variables de entorno
load_environment_variables()

# Crear servidor MCP RAG
mcp = FastMCP(name="RAGServer", description="Servidor de recuperación de información y contexto semántico")

# Base de conocimiento simulada (en producción sería una base vectorial real)
KNOWLEDGE_BASE = {
    "finanzas_personales": {
        "content": """
        Las finanzas personales incluyen la gestión de ingresos, gastos, ahorros e inversiones.
        Principios básicos:
        1. Registrar todos los ingresos y gastos
        2. Crear un presupuesto mensual
        3. Ahorrar al menos 10-20% de los ingresos
        4. Evitar deudas innecesarias
        5. Tener un fondo de emergencia
        """,
        "keywords": ["finanzas", "dinero", "presupuesto", "ahorro", "gasto", "ingreso"]
    },
    "categorias_gastos": {
        "content": """
        Categorías comunes de gastos:
        - Alimentación: supermercado, restaurantes, comida rápida
        - Transporte: combustible, transporte público, mantenimiento vehículo
        - Vivienda: alquiler, servicios, mantenimiento
        - Salud: medicina, consultas, seguros médicos
        - Entretenimiento: cine, streaming, hobbies
        - Educación: cursos, libros, material educativo
        """,
        "keywords": ["categorias", "gastos", "alimentacion", "transporte", "vivienda", "salud"]
    },
    "consejos_ahorro": {
        "content": """
        Consejos para ahorrar dinero:
        1. Usa la regla 50/30/20: 50% necesidades, 30% deseos, 20% ahorro
        2. Revisa gastos mensuales y elimina suscripciones no usadas
        3. Compara precios antes de comprar
        4. Cocina en casa en lugar de comer fuera
        5. Establece metas de ahorro específicas
        6. Automatiza transferencias a cuenta de ahorro
        """,
        "keywords": ["ahorro", "consejos", "dinero", "regla", "metas", "automatizar"]
    }
}

class SimpleEmbedding:
    """Simulador simple de embeddings para búsqueda semántica"""
    
    @staticmethod
    def similarity_score(query: str, content: Dict[str, Any]) -> float:
        """Calcula un score de similitud simple basado en palabras clave"""
        query_words = set(query.lower().split())
        keywords = set(content.get("keywords", []))
        
        # Intersección de palabras
        common_words = query_words.intersection(keywords)
        
        if not keywords:
            return 0.0
        
        # Score basado en proporción de palabras coincidentes
        base_score = len(common_words) / len(keywords)
        
        # Bonus si hay palabras exactas en el contenido
        content_text = content.get("content", "").lower()
        exact_matches = sum(1 for word in query_words if word in content_text)
        bonus = exact_matches * 0.1
        
        return min(base_score + bonus, 1.0)

@mcp.tool()
def buscar_informacion(query: str, max_results: int = 3) -> dict:
    """
    Busca información relevante en la base de conocimiento usando similitud semántica.
    
    Args:
        query: Consulta o pregunta del usuario
        max_results: Número máximo de resultados a devolver
    """
    
    results = []
    
    for doc_id, content in KNOWLEDGE_BASE.items():
        score = SimpleEmbedding.similarity_score(query, content)
        
        if score > 0.1:  # Umbral mínimo de relevancia
            results.append({
                "document_id": doc_id,
                "content": content["content"],
                "relevance_score": score,
                "keywords": content["keywords"]
            })
    
    # Ordenar por score de relevancia
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return {
        "query": query,
        "results": results[:max_results],
        "total_found": len(results)
    }

@mcp.tool()
def expandir_contexto(user_input: str, context_history: str = "") -> dict:
    """
    Expande el contexto de una consulta con información relevante.
    
    Args:
        user_input: Entrada actual del usuario
        context_history: Historial de conversación (opcional)
    """
    
    # Buscar información relevante
    search_results = buscar_informacion(user_input)
    
    # Construir contexto expandido
    expanded_context = {
        "original_input": user_input,
        "relevant_information": [],
        "suggestions": [],
        "context_enhanced": False
    }
    
    if search_results["results"]:
        expanded_context["context_enhanced"] = True
        
        for result in search_results["results"]:
            expanded_context["relevant_information"].append({
                "source": result["document_id"],
                "content": result["content"][:200] + "...",  # Truncar para no sobrecargar
                "relevance": result["relevance_score"]
            })
        
        # Generar sugerencias basadas en el contexto
        if any("ahorro" in r["keywords"] for r in search_results["results"]):
            expanded_context["suggestions"].append("¿Te gustaría conocer consejos específicos de ahorro?")
        
        if any("gasto" in r["keywords"] for r in search_results["results"]):
            expanded_context["suggestions"].append("¿Quieres revisar tus categorías de gastos?")
    
    return expanded_context

@mcp.tool()
def generar_respuesta_contextual(query: str, datos_financieros: str = "") -> dict:
    """
    Genera una respuesta enriquecida con contexto relevante.
    
    Args:
        query: Pregunta del usuario
        datos_financieros: Datos financieros actuales del usuario (JSON)
    """
    
    # Expandir contexto
    context = expandir_contexto(query)
    
    # Buscar información específica
    search_info = buscar_informacion(query)
    
    response = {
        "query": query,
        "enhanced_response": "",
        "context_used": context["context_enhanced"],
        "additional_info": [],
        "recommendations": []
    }
    
    # Generar respuesta basada en contexto
    if context["context_enhanced"]:
        relevant_info = context["relevant_information"][0] if context["relevant_information"] else None
        
        if relevant_info:
            response["enhanced_response"] = f"""
            Basándome en tu consulta sobre {query}, te puedo proporcionar la siguiente información:
            
            {relevant_info['content']}
            
            Fuente: {relevant_info['source']}
            """
            
            response["additional_info"] = context["relevant_information"][1:] if len(context["relevant_information"]) > 1 else []
            response["recommendations"] = context["suggestions"]
    
    else:
        response["enhanced_response"] = "No encontré información específica en mi base de conocimiento, pero puedo ayudarte con consultas generales sobre finanzas."
    
    return response

@mcp.resource("rag://knowledge_base")
def obtener_base_conocimiento() -> str:
    """Proporciona acceso a toda la base de conocimiento"""
    return json.dumps(KNOWLEDGE_BASE, indent=2, ensure_ascii=False)

@mcp.resource("rag://stats")
def estadisticas_rag() -> str:
    """Proporciona estadísticas del sistema RAG"""
    stats = {
        "documents_in_kb": len(KNOWLEDGE_BASE),
        "total_keywords": sum(len(doc.get("keywords", [])) for doc in KNOWLEDGE_BASE.values()),
        "kb_topics": list(KNOWLEDGE_BASE.keys())
    }
    return json.dumps(stats, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    print("🧠 Iniciando servidor MCP RAG...")
    print("💡 Herramientas disponibles:")
    print("   - buscar_informacion: Búsqueda semántica en base de conocimiento")
    print("   - expandir_contexto: Enriquecimiento de contexto conversacional")
    print("   - generar_respuesta_contextual: Respuestas mejoradas con RAG")
    print("📊 Recursos disponibles:")
    print("   - rag://knowledge_base: Base de conocimiento completa")
    print("   - rag://stats: Estadísticas del sistema RAG")
    print("")
    mcp.run()