# 🧠 EconomIAssist

EconomIAssist is a personal financial assistant that interacts with users naturally through WhatsApp to manage income, expenses, habits, and reminders using Google Sheets and Google Calendar. Built on a modular architecture with NLP capabilities and connected via MCP (Message Communication Protocol).
---

## 🎯 Motivation and Objective
In the context of:

* Low financial literacy

* Daily financial decision complexity

* Need for accessible conversational assistants

* This project aims to create an intelligent chatbot that helps users manage their personal finances in a simple, conversational way.

---

## ✨ Key Features
* 📊 Track finances: Log income and expenses automatically via WhatsApp.

* ❓ Answer financial questions accurately and clearly.

* 🚨 Alert users about excessive spending or inefficient habits.

* 🧾 Generate reports with graphs and summaries from Google Sheets.

* 🗓️ Set calendar reminders for payments and financial events.

---

## 📁 Project Structure

```
├── src/
│ ├── agent/ # NLP processing (intent detection, entity extraction)
│ ├── integrations/ # Interfaces to WhatsApp, Google Sheets, and Google Calendar
│ ├── mcp/ # Message Communication Protocol components
│ ├── workflows/ # Business logic workflows and orchestration
│ ├── utils/ # Shared utility functions
│
├── tests/ # Unit and integration tests
├── scripts/ # Dev/ops scripts (e.g., setup, deployment)
├── config/ # Config files (e.g., API keys, environment settings)
├── docs/ # Documentation (architecture, onboarding, API)
├── .gitignore
├── requirements.txt
├── README.md
```
---

## 🔌 Tools & Integrations
* WhatsApp (Twilio): Communication channel with the user.

* Google Sheets: Acts as a financial backend.

* Google Calendar: Creates and manages financial reminders.

* MCP (Message Communication Protocol): Handles communication between modules.

* Graphing Tools: For visual financial summaries.

* Internet Access: To validate or extend financial information.

* RAG & RLHF: Used for retrieval and quality scoring of responses.

---

## 📈 Metrics & Evaluation
* ✅ Data logging precision

* 🧠 First-contact resolution rate

* ⭐ Conversation quality scored via RLHF

---

## 👥 Team
* Olivia Browne Corbacho – ocorbacho@udesa.edu.ar

* Maximo Simian – msimian@udesa.edu.ar

* Agustin Manzano – amanzano@udesa.edu.ar

* Manuel Ramirez Silva – mramirezsilva@udesa.edu.ar

---

## 🤖 Integración con OpenAI Agents

1. Instala dependencias:  
   ```bash
   pip install -r requirements.txt
   ```
2. Define tu configuración en `config/agent_config.yaml`.  
3. Ejecuta el agente:  
   ```bash
   python -c "from src.agent.openai_agent import run_agent; print(run_agent('¿Cuál es mi saldo actual?'))"
   ```
4. Integra este flujo en tu orquestador de WhatsApp o UI.

---

## 🚀 Instalación rápida (Linux/Mac)

1. **Clona el repositorio y entra a la carpeta del proyecto:**
   ```bash
   git clone <repo-url>
   cd EconomIAssist
   ```
2. **Ejecuta el script de setup automático:**
   ```bash
   bash setup.sh
   ```
   Esto instalará:
   - Todas las dependencias Python (`requirements.txt`)
   - El paquete Node.js `tavily-mcp` (usado para web search vía MCP)

3. **Configura tus variables de entorno en `.env`** (ejemplo: `TAVILY_API_KEY`, claves de Azure, etc).

4. **¡Listo! Ya puedes ejecutar el agente conversacional o los tests.**

---

> Si no tienes Node.js, instálalo desde https://nodejs.org/ (versión 18+ recomendada). Si usas Mac, puedes instalarlo con Homebrew: `brew install node`.
