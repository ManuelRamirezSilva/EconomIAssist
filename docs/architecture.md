# 🏗️ Architecture Overview – EconomIAssist
EconomIAssist es un asistente financiero personal conversacional que utiliza IA para gestionar finanzas personales. Aprovecha NLP para entender entrada del usuario, almacena datos financieros usando servidores MCP especializados, y opera usando una arquitectura modular basada en MCP (Model Context Protocol).

---
## 🧱 System Components
```
Usuario → Agente Conversacional → MCP Manager → Servidores MCP:
    - Knowledge Base (Memoria)
    - Google Sheets (Datos financieros)
    - Google Calendar (Recordatorios)
    - Tavily (Búsqueda web)
    - Calculator (Cálculos)
```
---

## 🔁 Response Process Flow

1.  **Receive**:
    * El usuario envía un mensaje, como:
        * ```"Gasté $2000 en comida hoy"```
        * ```"Me pagaron el sueldo de $120.000"```

2. **Understand**:
    * El agente NLP procesa la entrada para detectar intención y extraer entidades.

3. **Generate**:
    * El sistema determina la respuesta apropiada o acción usando herramientas MCP.

4. **Respond**:
    * Se envía una respuesta al usuario con confirmación o información relevante.
    * El sistema actualiza los backends (Knowledge Base, Google Sheets/Calendar).

---

## 📦 Modules and Responsibilities

Module|Description
---|---
```src/agent/```| Pipeline NLP: detección de intención, reconocimiento de entidades, comprensión de consultas
```src/mcp_servers/```|Servidores MCP personalizados (ej: BCRA server)
```src/utils/```|Sistema de logging estructurado para agente, intenciones y MCP
```config/```|Configuración de servidores MCP e instrucciones del sistema
```tests/```|Suite completa de pruebas para todos los componentes

---

## 🔌 External Integrations

Integration|	Role
---|---
**Azure OpenAI**	|Motor de IA principal para procesamiento de lenguaje natural
**Knowledge Base Server**	|Almacenamiento persistente de memoria conversacional
**Google Sheets**	|Almacenamiento de datos financieros estructurados
**Google Calendar**	|Gestión de recordatorios y eventos programados
**Tavily Search**	|Acceso a información financiera en tiempo real
**Calculator Server**	|Cálculos matemáticos precisos y confiables

