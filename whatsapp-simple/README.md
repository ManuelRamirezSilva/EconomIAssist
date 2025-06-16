# WhatsApp Bridge Simple para EconomIAssist

**Versión minimalista de integración WhatsApp con EconomIAssist + Sistema de Filtros Inteligentes**

Esta es una implementación ultra-simple de Baileys que actúa como puente entre WhatsApp y EconomIAssist, con sistema avanzado de filtros para controlar cuándo responde el bot.

## 🎯 Características

- **Ultra-ligero**: Solo 150 líneas de código base + filtros inteligentes
- **Sistema de filtros**: 5 modos diferentes para controlar respuestas
- **Sin TypeScript**: JavaScript puro para simplicidad
- **Sin dashboard web**: Solo terminal
- **Reconexión automática**: Maneja desconexiones
- **Contexto completo**: Envía toda la información del mensaje

## 🎛️ **NUEVA FUNCIONALIDAD: Sistema de Filtros**

Ahora puedes controlar exactamente cuándo responde el bot configurando diferentes modos:

### **Modos Disponibles:**

1. **`always`** - Responde a TODOS los mensajes (comportamiento original)
2. **`command`** - Solo responde si el mensaje empieza con `/eco`
3. **`mention`** - Solo responde si mencionan palabras financieras
4. **`whitelist`** - Solo responde a números/grupos específicos
5. **`smart`** - Combinación inteligente de todos los filtros ⭐ **RECOMENDADO**

## 🚀 Instalación Rápida

```bash
# 1. Instalar dependencias
npm install

# 2. Configurar filtros (IMPORTANTE)
cp .env.example .env
nano .env  # Editar configuración

# 3. Ejecutar
npm start
```

## 🔧 Configuración de Filtros

Edita el archivo `.env` en `whatsapp-simple/`:

```bash
# MODO DE RESPUESTA (elige uno)
RESPONSE_MODE=smart

# COMANDO DE ACTIVACIÓN 
BOT_COMMAND=/eco

# PALABRAS CLAVE FINANCIERAS
ACTIVATION_KEYWORDS=economIAssist,gasto,dinero,sueldo,finanzas,presupuesto,pagar,comprar,ahorro

# NÚMEROS PERMITIDOS (opcional)
WHITELISTED_NUMBERS=5491234567890,5499876543210

# GRUPOS PERMITIDOS (opcional) 
WHITELISTED_GROUPS=Familia,Finanzas Personales

# HORARIOS DE ACTIVIDAD
ACTIVE_HOURS_START=08:00
ACTIVE_HOURS_END=22:00

# RESPUESTA CUANDO NO PUEDE RESPONDER
AUTO_RESPONSE_DISABLED=🤖 Hola! Soy EconomIAssist. Para activarme, usa "/eco" o menciona palabras sobre finanzas.
```

## 📱 Ejemplos de Uso

### **Modo `smart` (Recomendado):**

✅ **Responderá a:**
- `"/eco ¿cuál es mi saldo?"`
- `"gasté 500 pesos en almuerzo"`
- `"necesito ayuda con mis finanzas"`
- Mensajes de números en whitelist
- Mensajes en grupos permitidos

❌ **NO responderá a:**
- `"hola ¿cómo estás?"`
- `"¿vieron el partido?"`
- Mensajes fuera del horario configurado
- Números/grupos no autorizados (si están configurados)

### **Modo `command`:**
- Solo responde a mensajes que empiecen con `/eco`
- Ejemplo: `"/eco registra un gasto de 1000 pesos"`

### **Modo `mention`:**
- Solo responde si mencionas palabras como "dinero", "gasto", "finanzas"
- Ejemplo: `"¿cómo registro un gasto?"` ✅
- Ejemplo: `"hola mundo"` ❌

## 🎯 **Configuraciones Recomendadas por Escenario:**

### **Para uso personal (solo tú):**
```bash
RESPONSE_MODE=smart
WHITELISTED_NUMBERS=tu_numero_aqui
BOT_COMMAND=/eco
```

### **Para grupo familiar:**
```bash
RESPONSE_MODE=smart  
WHITELISTED_GROUPS=Familia
ACTIVATION_KEYWORDS=economIAssist,gasto,dinero,finanzas
```

### **Para uso público controlado:**
```bash
RESPONSE_MODE=command
BOT_COMMAND=/eco
ACTIVE_HOURS_START=09:00
ACTIVE_HOURS_END=18:00
```

## 🔍 Logs y Debugging

Con `SHOW_FILTER_LOGS=true` verás logs detallados:

```
🔍 Evaluando filtros para: 123456789 | Mensaje: "hola como estas..." | Grupo: N/A
🧠 Modo inteligente:
   📝 Comando: ❌
   🔑 Palabra clave: ❌  
   👤 Whitelist: ✅
   🎯 Resultado: ✅ RESPONDER
```

## 🛠️ **Comparación con versión anterior:**

| Característica | Versión Anterior | Nueva Versión |
|---|---|---|
| **Control de respuestas** | ❌ Responde a todo | ✅ 5 modos de filtro |
| **Comandos** | ❌ | ✅ `/eco comando` |
| **Palabras clave** | ❌ | ✅ Solo temas financieros |
| **Whitelist** | ❌ | ✅ Números/grupos permitidos |
| **Horarios** | ❌ | ✅ Solo ciertos horarios |
| **Logs de filtros** | ❌ | ✅ Debug completo |

## 🎉 **Resultado:**

Ahora tienes **control total** sobre cuándo responde tu bot:

- **En grupos**: Solo cuando mencionan finanzas o usan `/eco`
- **Privado**: Solo números autorizados o con comando/palabras clave
- **Horarios**: Solo durante horas de trabajo
- **Sin spam**: No más respuestas a mensajes irrelevantes

---

**🎛️ ¡Control inteligente de respuestas implementado!**