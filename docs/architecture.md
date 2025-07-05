# 🏗️ Architecture Overview – EconomIAssist

EconomIAssist es un asistente financiero personal conversacional que utiliza IA para gestionar finanzas personales. Aprovecha NLP para entender la entrada del usuario, almacena datos financieros usando servidores MCP especializados, y opera usando una arquitectura modular basada en MCP (Model Context Protocol).

---

## 🧱 System Components

### Usuario
El usuario interactúa con el sistema mediante texto o voz, enviando consultas financieras o solicitudes de gestión.

### Conversational Agent
El agente conversacional es el núcleo del sistema, encargado de procesar las consultas del usuario y generar respuestas. Sus componentes principales incluyen:
- **IntentParser**: Detecta la intención del usuario y extrae entidades relevantes.
- **MemoryManager**: Maneja el contexto conversacional y la memoria persistente.
- **AgentCore**: Coordina las interacciones entre el usuario y las herramientas disponibles.

### MCP Layer
La capa MCP conecta el agente conversacional con los servidores MCP especializados. Incluye:
- **MCPManager**: Coordina las conexiones y descubrimiento de herramientas.
- **MCPServerRegistry**: Registra los servidores MCP disponibles.
- **MCPConnections**: Establece comunicación con los servidores mediante JSON-RPC.

### Servidores MCP
Los servidores MCP son módulos especializados que ofrecen funcionalidades específicas:
- **TavilyServer**: Realiza búsquedas web en tiempo real.
- **FinancialServer**: Gestiona datos financieros estructurados.
- **CalendarServer**: Maneja eventos y recordatorios en Google Calendar.
- **BCRAServer**: Proporciona datos económicos del Banco Central de la República Argentina.
- **MarketsServer**: Ofrece información sobre mercados financieros.

### WhatsApp Integration
La integración con WhatsApp permite a los usuarios interactuar con EconomIAssist directamente desde su dispositivo móvil. Incluye:
- **WhatsApp Bridge**: Captura mensajes de WhatsApp y los redirige al servidor HTTP de EconomIAssist.
- **EconomIAssist HTTP Server**: Procesa los mensajes recibidos y genera respuestas.
- **Message Adapter**: Adapta el contexto de WhatsApp para el agente conversacional.

---

## 🔁 Response Process Flow

1. **Receive**:
   - El usuario envía una consulta, como: "Gasté $2000 en comida hoy."
2. **Understand**:
   - El agente procesa la entrada para detectar intención y extraer entidades.
3. **Generate**:
   - El sistema determina la herramienta adecuada para responder.
4. **Respond**:
   - Se envía una respuesta al usuario y se actualizan los backends.

---

## 📦 Modules and Responsibilities

| Module               | Description                                                                 |
|-----------------------|-----------------------------------------------------------------------------|
| `src/agent/`          | Pipeline NLP: detección de intención, reconocimiento de entidades.         |
| `src/mcp_servers/`    | Servidores MCP personalizados (ej: BCRA server).                           |
| `src/utils/`          | Sistema de logging estructurado para agente, intenciones y MCP.           |
| `src/whatsapp/`       | Servidor HTTP para integración con WhatsApp.                              |
| `whatsapp-simple/`    | Bridge minimalista para capturar mensajes de WhatsApp.                    |
| `config/`             | Configuración de servidores MCP e instrucciones del sistema.              |
| `tests/`              | Suite completa de pruebas para todos los componentes.                     |

---

## 🔌 External Integrations

| Integration          | Role                                                                       |
|-----------------------|---------------------------------------------------------------------------|
| **Azure OpenAI**      | Motor de IA principal para procesamiento de lenguaje natural.            |
| **Knowledge Base**    | Almacenamiento persistente de memoria conversacional.                    |
| **Google Sheets**     | Almacenamiento de datos financieros estructurados.                       |
| **Google Calendar**   | Gestión de recordatorios y eventos programados.                         |
| **Tavily Search**     | Acceso a información financiera en tiempo real.                         |
| **Calculator Server** | Cálculos matemáticos precisos y confiables.                             |
| **WhatsApp Bridge**   | Comunicación entre WhatsApp y EconomIAssist.                            |

---

## 🧪 Evaluation Metrics

El sistema se evalúa mediante las siguientes métricas:
- **FCR (First Contact Resolution)**: Resolución en la primera interacción.
- **Precisión por intención**: Identificación correcta de la intención del usuario.
- **Latencia promedio**: Tiempo de respuesta del sistema.
- **Evaluación semántica automática**: Comparación de embeddings de respuesta.
- **Evaluación humana**: Ranking de calidad mediante formularios.
- **Tasa de éxito de ejecución**: Éxito en llamadas JSON-RPC.
- **Cobertura de herramientas**: Proporción de intents resueltos.

---

## 🛠️ Technical Considerations

- **Protocolo de comunicación**: JSON-RPC 2.0 sobre HTTP.
- **Modelo base**: Azure OpenAI GPT-4.1.
- **Discovery automático**: El cliente consulta el directorio MCP para descubrir herramientas disponibles.
- **Fallback a RAG**: Recuperación de información mediante embeddings si ninguna herramienta puede resolver la intención.
- **Memoria semántica**: Contexto histórico combinado con recuperación RAG.

---