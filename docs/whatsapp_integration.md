# Integración WhatsApp con EconomIAssist

## 🎯 Descripción

Esta integración permite usar EconomIAssist directamente desde WhatsApp mediante un bridge simplificado de Baileys. Los usuarios pueden enviar mensajes a WhatsApp y recibir respuestas inteligentes procesadas por EconomIAssist con todas sus capacidades MCP.

## 🏗️ Arquitectura

```
Usuario WhatsApp → WhatsApp Bridge → EconomIAssist HTTP Server → Conversational Agent → MCP Servers
                 (whatsapp-simple)   (FastAPI)                 (existente)       (existente)
```

### Componentes:

1. **WhatsApp Bridge** (`whatsapp-simple/`): Versión minimalista de Baileys (150 líneas)
2. **EconomIAssist HTTP Server** (`src/whatsapp/`): Servidor FastAPI que recibe mensajes
3. **Message Adapter** (`src/whatsapp/message_adapter.py`): Adaptador de contexto WhatsApp
4. **Script Coordinado** (`start_whatsapp.sh`): Inicia ambos servicios automáticamente

## 🚀 Uso Rápido

```bash
# Iniciar la integración completa
./start_whatsapp.sh

# Escanear QR que aparece en terminal
# ¡Listo! Enviar mensajes por WhatsApp
```

## 📁 Estructura de Archivos

```
EconomIAssist/
├── whatsapp-simple/              # Bridge WhatsApp minimalista
│   ├── package.json              # Solo 4 dependencias
│   ├── whatsapp-bridge.js         # 150 líneas de código
│   ├── .env                       # Configuración simple
│   └── auth_session/              # Credenciales WhatsApp
├── src/whatsapp/                  # Servidor HTTP EconomIAssist
│   ├── whatsapp_server.py         # FastAPI server
│   ├── message_adapter.py         # Adaptador de mensajes
│   └── __init__.py
├── start_whatsapp.sh              # Script coordinado
└── .env                          # Configuración general (agregado WHATSAPP_*)
```

## 🔧 Configuración

### Variables de entorno agregadas a `.env`:
```bash
WHATSAPP_SERVER_HOST=localhost
WHATSAPP_SERVER_PORT=8000
```

### WhatsApp Bridge (whatsapp-simple/.env):
```bash
ECONOMÍ_ASSIST_URL=http://localhost:8000/whatsapp/message
BOT_NAME=EconomIAssist
```

## 📊 Flujo de Datos

1. **Usuario envía mensaje** por WhatsApp
2. **WhatsApp Bridge** captura el mensaje y extrae:
   - Texto del mensaje
   - ID del chat/grupo
   - Número del remitente
   - Timestamp
   - Contexto del grupo (si aplica)
3. **Bridge hace GET request** a EconomIAssist:
   ```
   GET http://localhost:8000/whatsapp/message?message=hola&fromJid=123@s.whatsapp.net&isGroup=false&senderNumber=123456789
   ```
4. **EconomIAssist HTTP Server** recibe y procesa:
   - Usa `WhatsAppMessageAdapter` para contexto
   - Llama al `ConversationalAgent` existente
   - Procesa con todos los servidores MCP
5. **Respuesta se envía** de vuelta por WhatsApp

## 🔍 Endpoints Disponibles

- `GET /` - Estado general del servidor
- `GET /health` - Verificación de salud
- `GET /whatsapp/message` - Endpoint principal (usado por bridge)
- `GET /whatsapp/test` - Endpoint de prueba

## 🎛️ Monitoreo

### Verificar estado del servidor:
```bash
curl http://localhost:8000/health
```

### Logs del sistema:
- **EconomIAssist**: Se muestran en terminal donde se ejecutó `start_whatsapp.sh`
- **WhatsApp Bridge**: Se muestran en la misma terminal
- **MCP Servers**: En archivos de log habituales (`logs/`)

## 🔄 Flujo de Inicio

1. **Script verifica dependencias**:
   - Entorno virtual Python
   - Node.js instalado
   - Dependencias npm del bridge

2. **Inicia EconomIAssist HTTP Server**:
   - Carga agente conversacional
   - Conecta servidores MCP
   - Escucha en puerto 8000

3. **Inicia WhatsApp Bridge**:
   - Se conecta a WhatsApp Web
   - Muestra QR para escanear
   - Redirige mensajes a EconomIAssist

## 🚨 Troubleshooting

### Error: "Servidor EconomIAssist no responde"
- Verificar que no haya otro proceso en puerto 8000
- Revisar credenciales de Azure OpenAI en `.env`
- Verificar que MCP servers estén funcionando

### Error: "WhatsApp Bridge no conecta"
- Verificar conexión a internet
- Escanear QR código nuevamente
- Revisar que `ECONOMÍ_ASSIST_URL` apunte a servidor correcto

### Error: "No se puede instalar dependencias npm"
- Verificar Node.js 16+ instalado
- Limpiar cache: `cd whatsapp-simple && rm -rf node_modules && npm install`

## 🎯 Ventajas de esta Implementación

### vs baileys-starter-main completo:
- ✅ **90% menos código** (150 vs 2000+ líneas)
- ✅ **95% menos dependencias** (4 vs 20+ paquetes)
- ✅ **Inicio 10x más rápido**
- ✅ **Más fácil de debuggear**
- ✅ **Sin TypeScript** (menos complejidad)
- ✅ **Sin dashboard web** (menos superficie de ataque)

### vs otras integraciones WhatsApp:
- ✅ **Contexto completo** del mensaje
- ✅ **Integración nativa** con EconomIAssist
- ✅ **Todas las capacidades MCP** disponibles
- ✅ **Memoria conversacional** por usuario
- ✅ **Reconexión automática**

## 📈 Capacidades Disponibles via WhatsApp

Todas las funcionalidades de EconomIAssist están disponibles:

- 🧠 **Memoria conversacional** (por usuario de WhatsApp)
- 📊 **Google Sheets** (registrar gastos/ingresos)
- 📅 **Google Calendar** (crear eventos/recordatorios)
- 🌐 **Búsqueda web** (Tavily para información actualizada)
- 🧮 **Calculadora** (cálculos precisos)
- 💱 **BCRA** (datos económicos argentinos)
- 🔍 **Knowledge Base** (memoria persistente)

## 🎉 Resultado Final

Los usuarios pueden ahora:
- Enviar **"gasté 500 pesos en almuerzo"** → Se registra automáticamente
- Preguntar **"¿cuál es mi saldo?"** → Consulta datos reales
- Pedir **"recordarme pagar impuestos mañana"** → Crea evento en calendar
- Consultar **"¿cómo está el dólar?"** → Busca cotización actual
- Y **todas las funcionalidades** de EconomIAssist ¡desde WhatsApp!

---

**🚀 ¡EconomIAssist ahora disponible 24/7 en WhatsApp!**