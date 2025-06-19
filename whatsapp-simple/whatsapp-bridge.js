const { default: makeWASocket, DisconnectReason, useMultiFileAuthState } = require('baileys')
const qrcode = require('qrcode-terminal')
const axios = require('axios')
const WebSocket = require('ws')
require('dotenv').config()

// Configuración
const ECONOMÍ_ASSIST_URL = process.env.ECONOMÍ_ASSIST_URL || 'http://localhost:8000/whatsapp/message'
const BOT_NAME = process.env.BOT_NAME || 'EconomIAssist'

// Configuración de filtros
const RESPONSE_MODE = process.env.RESPONSE_MODE || 'always'
const BOT_COMMAND = process.env.BOT_COMMAND || '/eco'
const ACTIVATION_KEYWORDS = process.env.ACTIVATION_KEYWORDS ? 
    process.env.ACTIVATION_KEYWORDS.split(',').map(k => k.trim().toLowerCase()) : []
const WHITELISTED_NUMBERS = process.env.WHITELISTED_NUMBERS ? 
    process.env.WHITELISTED_NUMBERS.split(',').map(n => n.trim()) : []
const WHITELISTED_GROUPS = process.env.WHITELISTED_GROUPS ? 
    process.env.WHITELISTED_GROUPS.split(',').map(g => g.trim().toLowerCase()) : []
const ACTIVE_HOURS_START = process.env.ACTIVE_HOURS_START || '00:00'
const ACTIVE_HOURS_END = process.env.ACTIVE_HOURS_END || '23:59'
const AUTO_RESPONSE_DISABLED = process.env.AUTO_RESPONSE_DISABLED || 
    '🤖 Hola! Soy EconomIAssist. Para activarme, usa "/eco" o menciona palabras sobre finanzas.'
const SHOW_FILTER_LOGS = process.env.SHOW_FILTER_LOGS === 'true'

console.log('🤖 Iniciando WhatsApp Bridge para EconomIAssist v2.0')
console.log(`📡 Servidor objetivo: ${ECONOMÍ_ASSIST_URL}`)
console.log(`🎯 Modo de respuesta: ${RESPONSE_MODE}`)

// Variables globales
let whatsappSocket = null
let responseQueue = new Map() // Para manejar respuestas pendientes

// Cola de respuestas para envío con delay humano
class ResponseQueue {
    constructor() {
        this.queue = []
        this.processing = false
    }
    
    async add(jid, message, delay = 0) {
        this.queue.push({ jid, message, delay })
        if (!this.processing) {
            this.processQueue()
        }
    }
    
    async processQueue() {
        this.processing = true
        
        while (this.queue.length > 0) {
            const { jid, message, delay } = this.queue.shift()
            
            try {
                if (delay > 0) {
                    console.log(`⏳ Esperando ${delay}ms antes de enviar respuesta...`)
                    await new Promise(resolve => setTimeout(resolve, delay))
                }
                
                if (whatsappSocket) {
                    await whatsappSocket.sendMessage(jid, { text: message })
                    console.log(`📤 Respuesta enviada a ${jid}: ${message.substring(0, 50)}...`)
                } else {
                    console.log('⚠️ Socket WhatsApp no disponible')
                }
            } catch (error) {
                console.error('❌ Error enviando respuesta:', error.message)
            }
        }
        
        this.processing = false
    }
}

const responseQueueManager = new ResponseQueue()

// Función para verificar si el bot debe responder
function shouldRespond(message, senderNumber, isGroup, groupName) {
    const messageText = message.toLowerCase()
    const currentTime = new Date().toLocaleTimeString('en-GB', { hour12: false }).slice(0, 5)
    
    // Log de filtro si está habilitado
    if (SHOW_FILTER_LOGS) {
        console.log(`🔍 Evaluando filtros para: ${senderNumber} | Mensaje: "${message.substring(0, 30)}..." | Grupo: ${isGroup ? groupName : 'N/A'}`)
    }
    
    // Verificar horario de actividad
    if (currentTime < ACTIVE_HOURS_START || currentTime > ACTIVE_HOURS_END) {
        if (SHOW_FILTER_LOGS) console.log(`⏰ Fuera de horario activo (${ACTIVE_HOURS_START}-${ACTIVE_HOURS_END})`)
        return false
    }
    
    switch (RESPONSE_MODE) {
        case 'always':
            return true
            
        case 'command':
            const hasCommand = messageText.startsWith(BOT_COMMAND.toLowerCase())
            if (SHOW_FILTER_LOGS) console.log(`📝 Comando "${BOT_COMMAND}": ${hasCommand ? '✅' : '❌'}`)
            return hasCommand
            
        case 'mention':
            const hasKeyword = ACTIVATION_KEYWORDS.some(keyword => messageText.includes(keyword))
            if (SHOW_FILTER_LOGS) console.log(`🔑 Palabras clave: ${hasKeyword ? '✅' : '❌'}`)
            return hasKeyword
            
        case 'whitelist':
            const numberAllowed = WHITELISTED_NUMBERS.length === 0 || WHITELISTED_NUMBERS.includes(senderNumber)
            const groupAllowed = !isGroup || WHITELISTED_GROUPS.length === 0 || 
                WHITELISTED_GROUPS.some(g => groupName && groupName.toLowerCase().includes(g))
            
            if (SHOW_FILTER_LOGS) {
                console.log(`👤 Número permitido: ${numberAllowed ? '✅' : '❌'}`)
                console.log(`👥 Grupo permitido: ${groupAllowed ? '✅' : '❌'}`)
            }
            return numberAllowed && groupAllowed
            
        case 'smart':
            // Modo inteligente: comando O palabra clave O whitelist
            const smartCommand = messageText.startsWith(BOT_COMMAND.toLowerCase())
            const smartKeyword = ACTIVATION_KEYWORDS.some(keyword => messageText.includes(keyword))
            const smartNumber = WHITELISTED_NUMBERS.length === 0 || WHITELISTED_NUMBERS.includes(senderNumber)
            const smartGroup = !isGroup || WHITELISTED_GROUPS.length === 0 || 
                WHITELISTED_GROUPS.some(g => groupName && groupName.toLowerCase().includes(g))
            
            const result = smartCommand || smartKeyword || (smartNumber && smartGroup)
            
            if (SHOW_FILTER_LOGS) {
                console.log(`🧠 Modo inteligente:`)
                console.log(`   📝 Comando: ${smartCommand ? '✅' : '❌'}`)
                console.log(`   🔑 Palabra clave: ${smartKeyword ? '✅' : '❌'}`)
                console.log(`   👤 Whitelist: ${smartNumber && smartGroup ? '✅' : '❌'}`)
                console.log(`   🎯 Resultado: ${result ? '✅ RESPONDER' : '❌ NO RESPONDER'}`)
            }
            return result
            
        default:
            return true
    }
}

// Función para procesar comando si existe
function processCommand(message) {
    if (message.toLowerCase().startsWith(BOT_COMMAND.toLowerCase())) {
        // Remover el comando del mensaje para enviar solo el contenido
        return message.substring(BOT_COMMAND.length).trim()
    }
    return message
}

async function startWhatsApp() {
    try {
        // Configurar autenticación de WhatsApp
        const { state, saveCreds } = await useMultiFileAuthState('./auth_session')
        
        // Crear socket de WhatsApp
        const sock = makeWASocket({
            auth: state,
            printQRInTerminal: false, // Lo haremos manualmente
            browser: ['EconomIAssist', 'Chrome', '1.0.0'],
            generateHighQualityLinkPreview: true,
            markOnlineOnConnect: false
        })

        // Guardar referencia global
        whatsappSocket = sock

        // Manejar actualizaciones de conexión
        sock.ev.on('connection.update', (update) => {
            const { connection, lastDisconnect, qr } = update
            
            if (qr) {
                console.log('\n🔗 Escanea este código QR con WhatsApp:')
                qrcode.generate(qr, { small: true })
                console.log('\n⏳ Esperando escaneo...')
            }
            
            if (connection === 'close') {
                const shouldReconnect = lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut
                
                if (shouldReconnect) {
                    console.log('🔄 Conexión perdida. Reconectando en 3 segundos...')
                    setTimeout(startWhatsApp, 3000)
                } else {
                    console.log('❌ Sesión cerrada. Escanea el QR nuevamente.')
                }
            } else if (connection === 'open') {
                console.log('✅ ¡Conectado a WhatsApp exitosamente!')
                console.log(`📱 Bot activo como: ${BOT_NAME}`)
                console.log(`🎯 Modo de filtros: ${RESPONSE_MODE}`)
                console.log('🧠 Conversation Manager v2.0: Activado')
                
                // Establecer conexión con servidor para recibir respuestas
                setupResponseListener()
            } else if (connection === 'connecting') {
                console.log('🔄 Conectando a WhatsApp...')
            }
        })

        // Guardar credenciales cuando se actualicen
        sock.ev.on('creds.update', saveCreds)

        // Manejar mensajes entrantes
        sock.ev.on('messages.upsert', async ({ messages, type }) => {
            // Solo procesar mensajes nuevos
            if (type !== 'notify') return

            for (const message of messages) {
                await handleMessage(sock, message)
            }
        })

    } catch (error) {
        console.error('❌ Error iniciando WhatsApp:', error)
        console.log('🔄 Reintentando en 5 segundos...')
        setTimeout(startWhatsApp, 5000)
    }
}

function setupResponseListener() {
    console.log('🔗 Configurando listener para respuestas del servidor...')
    
    // Polling periódico para verificar respuestas pendientes
    setInterval(async () => {
        try {
            const response = await axios.get('http://localhost:8000/whatsapp/pending-responses')
            
            if (response.data && response.data.length > 0) {
                for (const pendingResponse of response.data) {
                    await responseQueueManager.add(
                        pendingResponse.jid,
                        pendingResponse.message,
                        pendingResponse.delay || 0
                    )
                }
            }
        } catch (error) {
            // Ignorar errores de polling silenciosamente
        }
    }, 1000) // Verificar cada segundo
}

async function handleMessage(sock, message) {
    try {
        // Saltar si no hay contenido o es mensaje propio
        if (!message.message || message.key.fromMe) return

        const remoteJid = message.key.remoteJid
        if (!remoteJid) return

        // Extraer texto del mensaje
        const text = message.message?.conversation || 
                    message.message?.extendedTextMessage?.text || ''
        
        if (!text) return

        // Determinar si es grupo
        const isGroup = remoteJid.endsWith('@g.us')
        const senderNumber = isGroup ? 
            message.key.participant?.split('@')[0] : 
            remoteJid.split('@')[0]

        // Obtener nombre del grupo si es necesario
        let groupName = null
        if (isGroup) {
            try {
                const groupMetadata = await sock.groupMetadata(remoteJid)
                groupName = groupMetadata.subject
            } catch (error) {
                console.log('⚠️ No se pudo obtener nombre del grupo')
            }
        }

        console.log(`📨 Mensaje recibido de ${senderNumber} ${isGroup ? `(grupo: ${groupName})` : '(privado)'}: ${text.substring(0, 50)}...`)

        // APLICAR FILTROS - Verificar si debe responder
        if (!shouldRespond(text, senderNumber, isGroup, groupName)) {
            console.log(`🚫 Filtros bloquean respuesta para ${senderNumber}`)
            
            // Enviar respuesta de "bot no disponible" solo en chats privados
            // para evitar spam en grupos
            if (!isGroup && AUTO_RESPONSE_DISABLED) {
                await sock.sendMessage(remoteJid, { text: AUTO_RESPONSE_DISABLED })
                console.log(`📤 Respuesta automática enviada a ${senderNumber}`)
            }
            return
        }

        console.log(`✅ Filtros permiten respuesta para ${senderNumber}`)

        // Procesar comando si existe
        const processedMessage = processCommand(text)

        // Preparar información del mensaje para EconomIAssist
        const messageInfo = {
            message: processedMessage,
            fromJid: remoteJid,
            isGroup: isGroup,
            senderNumber: senderNumber,
            timestamp: new Date().toISOString(),
            messageId: message.key.id,
            groupName: groupName
        }

        // Enviar a EconomIAssist v2.0 (ahora sin esperar respuesta inmediata)
        try {
            console.log('🔄 Enviando a EconomIAssist v2.0 (Conversation Manager)...')
            
            const response = await axios.get(ECONOMÍ_ASSIST_URL, {
                params: messageInfo,
                timeout: 5000 // Timeout más corto porque no esperamos respuesta inmediata
            })

            console.log('✅ Mensaje enviado al Conversation Manager')

        } catch (error) {
            console.error('❌ Error comunicándose con EconomIAssist:', error.message)
            
            // Mensaje de error amigable inmediato
            const errorMsg = 'Lo siento, hay un problema técnico temporalmente. Intenta de nuevo en unos minutos.'
            await sock.sendMessage(remoteJid, { text: errorMsg })
        }

    } catch (error) {
        console.error('❌ Error procesando mensaje:', error)
    }
}

// Manejar cierre limpio
process.on('SIGINT', () => {
    console.log('\n👋 Cerrando WhatsApp Bridge...')
    process.exit(0)
})

process.on('SIGTERM', () => {
    console.log('\n👋 Cerrando WhatsApp Bridge...')
    process.exit(0)
})

// Iniciar la aplicación
console.log(`🚀 Iniciando ${BOT_NAME} WhatsApp Bridge...`)
startWhatsApp()