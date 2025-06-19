const { default: makeWASocket, DisconnectReason, useMultiFileAuthState } = require('baileys')
const qrcode = require('qrcode-terminal')

// Configurar SSL para desarrollo
process.env["NODE_TLS_REJECT_UNAUTHORIZED"] = 0

console.log('🚀 Iniciando WhatsApp Bridge Simplificado...')
console.log('🔧 Configuración SSL deshabilitada para desarrollo')

async function startWhatsApp() {
    try {
        console.log('📁 Configurando autenticación...')
        
        // Limpiar sesión anterior si existe
        const fs = require('fs')
        if (fs.existsSync('./auth_session')) {
            console.log('🗑️ Eliminando sesión anterior...')
            fs.rmSync('./auth_session', { recursive: true, force: true })
        }
        
        const { state, saveCreds } = await useMultiFileAuthState('./auth_session')
        
        console.log('🔌 Creando conexión WhatsApp...')
        
        const sock = makeWASocket({
            auth: state,
            browser: ['EconomIAssist', 'Desktop', '1.0.0'],
            // Configuración mínima para máxima compatibilidad
            connectTimeoutMs: 60000,
            defaultQueryTimeoutMs: 0,
            keepAliveIntervalMs: 25000,
            logger: {
                level: 'silent',
                child: () => ({
                    level: 'silent',
                    debug: () => {},
                    info: () => {},
                    warn: () => {},
                    error: () => {},
                    fatal: () => {},
                    trace: () => {},
                    child: () => this
                }),
                debug: () => {},
                info: () => {},
                warn: () => {},
                error: () => {},
                fatal: () => {},
                trace: () => {}
            }
        })

        console.log('✅ Socket WhatsApp creado')

        sock.ev.on('connection.update', (update) => {
            const { connection, lastDisconnect, qr } = update
            
            console.log(`🔄 Estado: ${connection}`)
            
            if (qr) {
                console.log('\n' + '='.repeat(60))
                console.log('📱 ¡CÓDIGO QR DISPONIBLE!')
                console.log('='.repeat(60))
                
                try {
                    qrcode.generate(qr, { small: true })
                } catch (error) {
                    console.log('❌ Error generando QR en terminal')
                }
                
                console.log('\n🔗 Link alternativo:')
                console.log(`https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=${encodeURIComponent(qr)}`)
                console.log('\n' + '='.repeat(60))
                console.log('📱 Escanea el QR con WhatsApp Web')
                console.log('='.repeat(60) + '\n')
            }
            
            if (connection === 'open') {
                console.log('✅ ¡CONECTADO A WHATSAPP!')
                console.log('🎉 Ya puedes usar WhatsApp normalmente')
            }
            
            if (connection === 'close') {
                const shouldReconnect = lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut
                
                if (shouldReconnect) {
                    console.log('🔄 Reconectando en 5 segundos...')
                    setTimeout(startWhatsApp, 5000)
                } else {
                    console.log('❌ Sesión cerrada - reinicia el script')
                }
            }
        })

        sock.ev.on('creds.update', saveCreds)
        
        // Agregar timeout de seguridad
        setTimeout(() => {
            if (!sock.authState.creds.registered) {
                console.log('\n⚠️ TIMEOUT: No se pudo conectar en 2 minutos')
                console.log('💡 Intenta:')
                console.log('   1. Verificar conexión a internet')
                console.log('   2. Usar VPN si estás en una red restringida')
                console.log('   3. Reiniciar el router')
                console.log('   4. Probar en otro momento')
            }
        }, 120000) // 2 minutos
        
    } catch (error) {
        console.error('❌ Error:', error.message)
        console.log('🔄 Reintentando en 10 segundos...')
        setTimeout(startWhatsApp, 10000)
    }
}

// Manejar cierre
process.on('SIGINT', () => {
    console.log('\n👋 Cerrando...')
    process.exit(0)
})

// Iniciar
startWhatsApp()