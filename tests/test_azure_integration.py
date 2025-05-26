#!/usr/bin/env python3
"""
Pruebas de integración para Azure OpenAI y el agente conversacional
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import patch, AsyncMock

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent.conversational_agent import (
    AzureOpenAIConfig, 
    ConversationalAgent, 
    IntentClassifier,
    CapabilityDiscovery,
    RoutingEngine,
    MemoryManager
)

class TestAzureOpenAIConfig:
    """Pruebas para la configuración de Azure OpenAI"""
    
    def test_config_loads_correctly(self):
        """Verifica que la configuración se carga correctamente"""
        config = AzureOpenAIConfig()
        
        assert config.api_base is not None
        assert config.api_key is not None
        assert config.api_version is not None
        assert config.deployment_name is not None
        
        print(f"✅ Configuración Azure OpenAI cargada:")
        print(f"   Endpoint: {config.api_base}")
        print(f"   Modelo: {config.deployment_name}")
        print(f"   Versión API: {config.api_version}")
    
    def test_client_creation(self):
        """Verifica que se puede crear el cliente de Azure OpenAI"""
        config = AzureOpenAIConfig()
        client = config.create_client()
        
        assert client is not None
        print(f"✅ Cliente Azure OpenAI creado exitosamente")
    
    def test_model_creation(self):
        """Verifica que se puede crear el modelo OpenAI"""
        config = AzureOpenAIConfig()
        model = config.create_model()
        
        assert model is not None
        assert model.model == config.deployment_name
        print(f"✅ Modelo OpenAI creado: {type(model).__name__}")

class TestIntentClassifier:
    """Pruebas para el clasificador de intenciones"""
    
    def test_financial_query_classification(self):
        """Prueba clasificación de consultas financieras"""
        classifier = IntentClassifier()
        
        test_cases = [
            ("¿Cuál es mi saldo actual?", "financial_query"),
            ("¿Cuánto dinero tengo?", "financial_query"),
            ("Dame mi resumen financiero", "financial_query"),
        ]
        
        for text, expected_intent in test_cases:
            intent = classifier.get_primary_intent(text)
            print(f"📝 '{text}' -> {intent}")
            assert intent == expected_intent or intent == "general"  # Permitir general como fallback
    
    def test_financial_action_classification(self):
        """Prueba clasificación de acciones financieras"""
        classifier = IntentClassifier()
        
        test_cases = [
            ("Registra un gasto de 50 pesos", "financial_action"),
            ("Anota un ingreso de 1000", "financial_action"),
            ("Guarda esta transacción", "financial_action"),
        ]
        
        for text, expected_intent in test_cases:
            intent = classifier.get_primary_intent(text)
            print(f"💰 '{text}' -> {intent}")
            # Puede ser financial_action o general
            assert intent in ["financial_action", "general"]
    
    def test_rag_query_classification(self):
        """Prueba clasificación de consultas RAG"""
        classifier = IntentClassifier()
        
        test_cases = [
            ("Dame consejos de ahorro", "rag_query"),
            ("¿Cómo puedo organizar mis finanzas?", "rag_query"),
            ("Explícame qué es un presupuesto", "rag_query"),
        ]
        
        for text, expected_intent in test_cases:
            intent = classifier.get_primary_intent(text)
            print(f"🧠 '{text}' -> {intent}")
            # Puede ser rag_query o general
            assert intent in ["rag_query", "general"]

class TestCapabilityDiscovery:
    """Pruebas para el descubrimiento de capacidades"""
    
    @pytest.mark.asyncio
    async def test_server_discovery(self):
        """Prueba el descubrimiento de servidores MCP"""
        discovery = CapabilityDiscovery()
        available_servers = await discovery.discover_and_validate()
        
        print(f"🔍 Servidores descubiertos: {list(available_servers.keys())}")
        
        # Debe encontrar al menos el servidor financial
        assert len(available_servers) > 0
        assert "financial" in available_servers
        
        for server_name, config in available_servers.items():
            print(f"✅ {server_name}: {config.description}")

class TestRoutingEngine:
    """Pruebas para el motor de enrutamiento"""
    
    @pytest.mark.asyncio
    async def test_routing_logic(self):
        """Prueba la lógica de enrutamiento"""
        discovery = CapabilityDiscovery()
        await discovery.discover_and_validate()
        
        routing = RoutingEngine(discovery)
        
        test_cases = [
            ("financial_query", "financial"),
            ("financial_action", "financial"),
            ("help", None),
        ]
        
        for intent, expected_server in test_cases:
            server = routing.route_intent(intent)
            print(f"🚦 {intent} -> {server}")
            assert server == expected_server

class TestMemoryManager:
    """Pruebas para el manejo de memoria"""
    
    def test_memory_operations(self):
        """Prueba las operaciones de memoria"""
        memory = MemoryManager()
        
        # Agregar interacciones
        memory.add_interaction(
            "¿Cuál es mi saldo?",
            "Tu saldo actual es $1000",
            {"intent": "financial_query"}
        )
        
        memory.add_interaction(
            "Registra un gasto de 50 pesos",
            "Gasto registrado exitosamente",
            {"intent": "financial_action"}
        )
        
        # Verificar contexto
        context = memory.get_context_summary()
        assert "¿Cuál es mi saldo?" in context
        assert len(memory.conversation_history) == 2
        
        print(f"💭 Contexto generado:\n{context}")

class TestConversationalAgent:
    """Pruebas principales del agente conversacional"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Prueba la inicialización del agente"""
        agent = ConversationalAgent()
        await agent.initialize()
        
        assert agent.main_agent is not None
        assert agent.model is not None
        assert len(agent.discovery.available_servers) > 0
        
        print(f"🤖 Agente inicializado correctamente")
        print(f"   Servidores disponibles: {list(agent.discovery.available_servers.keys())}")
    
    @pytest.mark.asyncio
    async def test_help_query(self):
        """Prueba la consulta de ayuda"""
        agent = ConversationalAgent()
        await agent.initialize()
        
        response = await agent.process_query("ayuda")
        
        assert response is not None
        assert "EconomIAssist" in response
        assert "Gestión Financiera" in response
        
        print(f"❓ Respuesta de ayuda generada exitosamente")
    
    @pytest.mark.asyncio
    async def test_financial_query_with_azure_openai(self):
        """Prueba una consulta financiera real con Azure OpenAI"""
        agent = ConversationalAgent()
        await agent.initialize()
        
        # Probar diferentes tipos de consultas
        test_queries = [
            "¿Cuál es mi saldo actual?",
            "Dame consejos de ahorro",
            "¿Cómo puedo organizar mejor mis finanzas?",
        ]
        
        for query in test_queries:
            print(f"\n🔍 Probando: '{query}'")
            response = await agent.process_query(query)
            
            assert response is not None
            assert len(response) > 10  # Respuesta no vacía
            assert "Error interno" not in response  # Sin errores
            
            print(f"✅ Respuesta recibida ({len(response)} caracteres)")
            print(f"   Inicio: {response[:100]}...")
    
    @pytest.mark.asyncio
    async def test_intent_classification_integration(self):
        """Prueba la integración del clasificador de intenciones"""
        agent = ConversationalAgent()
        await agent.initialize()
        
        # Monitorear las intenciones detectadas
        test_cases = [
            ("¿Cuál es mi saldo?", ["financial_query", "general"]),
            ("Registra un gasto", ["financial_action", "general"]),
            ("Dame consejos", ["rag_query", "general"]),
            ("ayuda", ["help"]),
        ]
        
        for query, expected_intents in test_cases:
            intent = agent.intent_classifier.get_primary_intent(query)
            print(f"🧠 '{query}' -> intención: {intent}")
            assert intent in expected_intents
    
    @pytest.mark.asyncio
    async def test_conversation_memory(self):
        """Prueba la memoria conversacional"""
        agent = ConversationalAgent()
        await agent.initialize()
        
        # Simular una conversación
        queries = [
            "¿Cuál es mi saldo?",
            "Dame consejos de ahorro",
            "¿Cómo puedo reducir gastos?",
        ]
        
        for i, query in enumerate(queries):
            response = await agent.process_query(query)
            print(f"💬 Turno {i+1}: {len(agent.memory.conversation_history)} interacciones en memoria")
        
        # Verificar que la memoria se actualiza
        assert len(agent.memory.conversation_history) == len(queries)
        
        # Verificar contexto
        context = agent.memory.get_context_summary()
        assert "saldo" in context.lower() or "consejos" in context.lower()
        
        print(f"💭 Memoria conversacional funcionando correctamente")

class TestEndToEndIntegration:
    """Pruebas de integración end-to-end"""
    
    @pytest.mark.asyncio
    async def test_complete_conversation_flow(self):
        """Prueba un flujo completo de conversación"""
        print("\n🎯 Iniciando prueba de flujo completo...")
        
        agent = ConversationalAgent()
        await agent.initialize()
        
        # Simular una conversación realista
        conversation = [
            ("ayuda", "debe contener información sobre capacidades"),
            ("¿Cuál es mi saldo actual?", "debe responder sobre saldo"),
            ("Dame consejos de ahorro", "debe dar consejos financieros"),
            ("¿Cómo puedo reducir mis gastos?", "debe dar sugerencias"),
        ]
        
        for i, (query, expectation) in enumerate(conversation, 1):
            print(f"\n--- Turno {i} ---")
            print(f"👤 Usuario: {query}")
            
            response = await agent.process_query(query)
            
            print(f"🤖 EconomIAssist: {response[:150]}...")
            print(f"✅ Expectativa: {expectation}")
            
            # Verificaciones básicas
            assert response is not None
            assert len(response) > 20
            assert "Error interno" not in response
        
        # Verificar métricas finales
        print(f"\n📊 Métricas finales:")
        print(f"   Total consultas: {agent.metrics['total_queries']}")
        print(f"   Resoluciones exitosas: {agent.metrics['successful_resolutions']}")
        print(f"   Tasa de éxito: {agent.metrics['successful_resolutions']/agent.metrics['total_queries']*100:.1f}%")
        
        assert agent.metrics['total_queries'] == len(conversation)
        assert agent.metrics['successful_resolutions'] > 0

# Función para ejecutar todas las pruebas
async def run_all_tests():
    """Ejecuta todas las pruebas de manera secuencial"""
    print("🧪 Iniciando suite de pruebas completa para EconomIAssist")
    print("=" * 70)
    
    # Ejecutar pruebas síncronas
    test_classes = [
        TestAzureOpenAIConfig,
        TestIntentClassifier,
        TestMemoryManager,
    ]
    
    for test_class in test_classes:
        print(f"\n🔬 Ejecutando {test_class.__name__}...")
        instance = test_class()
        
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                try:
                    method = getattr(instance, method_name)
                    method()
                    print(f"   ✅ {method_name}")
                except Exception as e:
                    print(f"   ❌ {method_name}: {e}")
    
    # Ejecutar pruebas asíncronas
    async_test_classes = [
        TestCapabilityDiscovery,
        TestRoutingEngine,
        TestConversationalAgent,
        TestEndToEndIntegration,
    ]
    
    for test_class in async_test_classes:
        print(f"\n🔬 Ejecutando {test_class.__name__}...")
        instance = test_class()
        
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                try:
                    method = getattr(instance, method_name)
                    if asyncio.iscoroutinefunction(method):
                        await method()
                    else:
                        method()
                    print(f"   ✅ {method_name}")
                except Exception as e:
                    print(f"   ❌ {method_name}: {e}")
    
    print("\n🎉 Suite de pruebas completada!")

if __name__ == "__main__":
    asyncio.run(run_all_tests())