# 🤖 EconomIAssist

**Asistente Financiero Personal con IA Conversacional**

EconomIAssist es un agente conversacional inteligente que combina Azure OpenAI con Model Context Protocol (MCP) para ofrecer asistencia financiera personalizada.

## ✨ Características Principales

- 💬 **Conversación Natural**: Interfaz en español argentino
- 🧠 **IA Avanzada**: Powered by Azure OpenAI GPT-4o-mini
- 🔧 **Extensible**: Arquitectura MCP para nuevas capacidades
- 🌐 **Búsqueda Web**: Integración con Tavily para información actualizada
- 📊 **Gestión Financiera**: Seguimiento de ingresos, gastos y consejos

## 🚀 Instalación Rápida

```bash
# Clonar el repositorio
git clone <repository-url>
cd EconomIAssist

# Ejecutar setup automático
chmod +x setup.sh
./setup.sh
```

## ⚙️ Configuración

Crea un archivo `.env` en la raíz del proyecto:

```env
# Azure OpenAI (Requerido)
AZURE_OPENAI_API_BASE=tu_endpoint_azure
AZURE_OPENAI_API_KEY=tu_api_key_azure
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=tu_deployment_name

# OpenAI API Key (Opcional - para funciones avanzadas)
OPENAI_API_KEY=tu_openai_api_key

# Tavily API Key (Opcional - para búsqueda web)
TAVILY_API_KEY=tu_tavily_api_key
```

## 🏃‍♂️ Uso

### Ejecutar Pruebas
```bash
python tests/run_all_tests.py
```

### Usar el Agente
```bash
python src/agent/conversational_agent.py
```

### Ejemplos de Conversación
- "¿Cuál es mi saldo actual?"
- "Dame consejos de ahorro"
- "Registra un gasto de 500 pesos"
- "¿Cómo puedo mejorar mis finanzas?"

## 📁 Estructura del Proyecto

```
EconomIAssist/
├── src/
│   ├── agent/
│   │   ├── conversational_agent.py    # Agente principal
│   │   ├── intentParser.py           # Parser de intenciones
│   │   ├── mcp_client.py            # Cliente MCP
│   │   └── mcp_registry.py          # Registro de servidores MCP
│   ├── mcp_servers/
│   │   └── bcra_server.py           # Servidor BCRA
│   └── utils/
│       ├── agent_logger.py          # Logger del agente
│       ├── intent_logger.py         # Logger de intenciones
│       └── mcp_logger.py           # Logger MCP
├── tests/
│   ├── run_all_tests.py            # Suite de pruebas
│   ├── test_azure_connection.py    # Prueba Azure OpenAI
│   ├── test_knowledgebase_mcp_pure.py # Prueba Knowledge Base
│   ├── test_tavily_mcp.py         # Prueba MCP+Tavily
│   └── test_final_integration.py  # Prueba integración completa
├── config/
│   ├── mcp_servers.yaml           # Configuración servidores MCP
│   ├── system_instructions.txt    # Instrucciones del sistema
│   └── gcp-service-account.json   # Credenciales Google Cloud
├── docs/                          # Documentación
├── logs/                          # Archivos de log
├── .env                          # Variables de entorno
├── requirements.txt              # Dependencias Python
└── setup.sh                     # Script de configuración
```

## 🔧 Dependencias Principales

- **mcp**: Model Context Protocol
- **openai**: Azure OpenAI SDK
- **structlog**: Logging estructurado
- **pydantic**: Validación de datos
- **python-dotenv**: Gestión de variables de entorno

## 🧪 Pruebas

El proyecto incluye pruebas automatizadas para:
- ✅ Conectividad con Azure OpenAI
- ✅ Funcionamiento del OpenAI Agents SDK
- ✅ Integración MCP con Tavily

## 📖 Documentación

- [Arquitectura del Sistema](docs/architecture.md)
- [Integración de Agentes](docs/agents_integration.md)

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para más detalles.

## 👥 Contribuciones

¡Las contribuciones son bienvenidas! Por favor:
1. Fork el proyecto
2. Crea una rama para tu feature
3. Realiza tus cambios
4. Ejecuta las pruebas
5. Envía un Pull Request

---

**Desarrollado con ❤️ para la gestión financiera inteligente**
