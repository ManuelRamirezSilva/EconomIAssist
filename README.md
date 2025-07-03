# 🤖 EconomIAssist

**Asistente Financiero Personal con IA Conversacional**

EconomIAssist es un agente conversacional inteligente que combina Azure OpenAI con Model Context Protocol (MCP) para ofrecer asistencia financiera personalizada. Este proyecto está diseñado para ayudar a los usuarios a gestionar sus finanzas mediante una interfaz conversacional avanzada, integrando múltiples herramientas y capacidades.

---

## ✨ Características Principales

- 💬 **Conversación Natural**: Interfaz en español argentino.
- 🧠 **IA Avanzada**: Powered by Azure OpenAI GPT-4o-mini.
- 🔧 **Extensible**: Arquitectura MCP para nuevas capacidades.
- 🌐 **Búsqueda Web**: Integración con Tavily para información actualizada.
- 📊 **Gestión Financiera**: Seguimiento de ingresos, gastos y consejos.
- 🧮 **Cálculos Financieros**: Precisión en cálculos matemáticos y financieros.
- 📅 **Gestión de Agenda**: Integración con Google Calendar para recordatorios y eventos.
- 💾 **Memoria Conversacional**: Persistencia de datos financieros y personales.
- 📈 **Análisis Económico**: Insights basados en datos del BCRA y otros indicadores.

---

## 🚀 Instalación Rápida

```bash
# Clonar el repositorio
git clone <https://github.com/ManuelRamirezSilva/EconomIAssist.git>
cd EconomIAssist

# Ejecutar setup automático
chmod +x setup.sh
./setup.sh
```

---

## ⚙️ Configuración

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

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

# BCRA API Token (Opcional - para datos económicos argentinos)
BCRA_API_TOKEN=tu_bcra_api_token

# Google APIs (Opcional - para Calendar y Sheets)
GOOGLE_CLIENT_ID=tu_google_client_id
GOOGLE_CLIENT_SECRET=tu_google_client_secret
GOOGLE_CREDENTIALS_PATH=./config/gcp-service-account.json
```

---

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
- "Dame consejos de ahorro."
- "Registra un gasto de 500 pesos."
- "¿Cómo puedo mejorar mis finanzas?"
- "Agendame una reunion a las 5pm del 18/06."

---

## 📁 Estructura del Proyecto

```
EconomIAssist/
├── src/
│   ├── agent/
│   │   ├── conversational_agent.py    # Agente principal
│   │   ├── intentParser.py           # Parser de intenciones
│   │   ├── mcp_client.py             # Cliente MCP
│   │   ├── mcp_registry.py           # Registro de servidores MCP
│   │   └── rag_module.py             # Módulo RAG (Recuperación de Información)
│   ├── mcp_servers/
│   │   ├── bcra_server.py            # Servidor BCRA
│   │   └── google_calendar_server.py # Servidor Google Calendar
│   ├── utils/
│   │   ├── agent_logger.py           # Logger del agente
│   │   ├── intent_logger.py          # Logger de intenciones
│   │   └── mcp_logger.py             # Logger MCP
│   ├── whatsapp/
│   │   ├── whatsapp_server.py        # Servidor HTTP para WhatsApp
│   │   ├── message_adapter.py        # Adaptador de mensajes
│   │   └── __init__.py
├── tests/
│   ├── run_all_tests.py              # Suite de pruebas
│   ├── test_azure_connection.py      # Prueba Azure OpenAI
│   ├── test_knowledgebase_mcp_pure.py # Prueba Knowledge Base
│   ├── test_tavily_mcp.py            # Prueba MCP+Tavily
│   └── test_final_integration.py     # Prueba integración completa
├── whatsapp-simple/
│   ├── package.json                  # Configuración del bridge WhatsApp
│   ├── whatsapp-bridge.js            # Bridge WhatsApp
│   ├── .env.example                  # Ejemplo de configuración
│   └── auth_session/                 # Sesión de autenticación
├── EcoData/                          # Datos económicos para RAG
├── chroma_db/                        # Base de datos vectorial
├── config/
│   ├── mcp_servers.yaml              # Configuración servidores MCP
│   ├── system_instructions.txt       # Instrucciones del sistema
│   └── gcp-service-account.json      # Credenciales Google Cloud
├── docs/                             # Documentación
│   ├── architecture.md               # Arquitectura del sistema
│   ├── whatsapp_integration.md       # Integración WhatsApp
│   ├── google_calendar_setup.md      # Configuración Google Calendar
│   └── agent_architecture.puml       # Diagrama de arquitectura
├── logs/                             # Archivos de log
├── log_dashboard.py                  # Visualizador de logs
├── lb_viewer.py                      # Visualizador de base de datos
├── .env                              # Variables de entorno
├── requirements.txt                  # Dependencias Python
├── setup.sh                          # Script de configuración
├── start_whatsapp.sh                 # Script para iniciar WhatsApp Bridge
└── LICENSE                           # Licencia del proyecto
```

---

## 🔧 Dependencias Principales

- **mcp**: Model Context Protocol.
- **openai**: Azure OpenAI SDK.
- **structlog**: Logging estructurado.
- **pydantic**: Validación de datos.
- **python-dotenv**: Gestión de variables de entorno.
- **langchain**: Framework para recuperación de información (RAG).
- **chromadb**: Base de datos vectorial para embeddings.

---

## 🧪 Pruebas

El proyecto incluye pruebas automatizadas para:
- ✅ Conectividad con Azure OpenAI.
- ✅ Funcionamiento del OpenAI Agents SDK.
- ✅ Integración MCP con Tavily.
- ✅ Recuperación de información con RAG.

---

## 📖 Documentación

- [Arquitectura del Sistema](docs/architecture.md)
- [Integración de Agentes](docs/agents_integration.md)
- [Prompts y Ejemplos](docs/prompts.md)

---

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para más detalles.

---

## 📝 Evaluaciones

### Evaluación Interna
- [Formulario de Feedback Interno](https://docs.google.com/forms/d/e/1FAIpQLScNQaLs5PXwIgjEpc5N4z-3gFBIpHkTSxjmtMiLvxT6Y1Wi0A/viewform?usp=header)

### Evaluación Externa
- [Formulario de Feedback Externo](https://docs.google.com/forms/d/e/1FAIpQLScg7l7IWAlfRXbIh0jC7yKpS2VIrpBaJlcBL8PyJIyXb36afQ/viewform?usp=sharing)

### Queries de Evaluacion
- [Documento de Google Docs con queries](https://docs.google.com/document/d/1dUF09JYsU9dbXFYDBa7wKmzJkiaqvPCdPWafexXeERw/edit?tab=t.0#heading=h.afpnys3d2kd9)

---

## 👥 Contribuciones

¡Las contribuciones son bienvenidas! Por favor:
1. Fork el proyecto.
2. Crea una rama para tu feature.
3. Realiza tus cambios.
4. Ejecuta las pruebas.
5. Envía un Pull Request.

---

---

## 👥 Team

* Olivia Browne Corbacho – ocorbacho@udesa.edu.ar

* Maximo Simian – msimian@udesa.edu.ar

* Agustin Manzano – amanzano@udesa.edu.ar

* Manuel Ramirez Silva – mramirezsilva@udesa.edu.ar

**Desarrollado con ❤️ para la gestión financiera inteligente**
