# Configuración de Google Calendar MCP Server

## 📋 Requisitos
- Node.js v16 o superior
- Cuenta de Google Cloud Platform
- API de Google Calendar habilitada

## 🔧 Configuración de Google Cloud

### 1. Crear proyecto en Google Cloud Console
1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Anota el `PROJECT_ID` para usarlo después

### 2. Habilitar Google Calendar API
1. Ve a "APIs & Services" > "Library"
2. Busca "Google Calendar API"
3. Haz clic en "Enable"

### 3. Configurar OAuth Consent Screen
1. Ve a "APIs & Services" > "OAuth consent screen"
2. Selecciona "External" (o "Internal" si usas Google Workspace)
3. Completa la información requerida:
   - App name: `EconomIAssist Calendar`
   - User support email: (tu email)
   - Developer contact: (tu email)
4. Agregar scopes:
   - Haz clic en "Add or Remove Scopes"
   - Busca y selecciona: `https://www.googleapis.com/auth/calendar.events`
5. Agregar tu email como usuario de prueba

### 4. Crear credenciales OAuth
1. Ve a "Credentials"
2. Haz clic en "Create Credentials" > "OAuth client ID"
3. Selecciona "Desktop app" como tipo de aplicación
4. Nómbralo: "EconomIAssist Calendar Client"
5. Descarga el archivo JSON

### 5. Configurar el archivo de credenciales
1. Abre el archivo JSON descargado
2. Copia los valores al archivo `config/gcp-oauth.keys.json`:
   - `client_id`: Reemplaza `YOUR_CLIENT_ID`
   - `project_id`: Reemplaza `YOUR_PROJECT_ID`
   - `client_secret`: Reemplaza `YOUR_CLIENT_SECRET`

## 🚀 Uso

Una vez configurado, el servidor MCP se conectará automáticamente usando:
```bash
npx -y mcp-google-calendar
```

### Autenticación (primera vez)
1. La primera vez se abrirá una ventana del navegador
2. Inicia sesión con tu cuenta de Google
3. Otorga los permisos de calendario solicitados
4. El token se guardará automáticamente para futuros usos

## 📝 Capacidades disponibles
- ✅ Listar calendarios
- ✅ Crear eventos
- ✅ Listar eventos
- ✅ Actualizar eventos
- ✅ Eliminar eventos
- ✅ Buscar disponibilidad

## 🔒 Seguridad
- ⚠️ Nunca subas `gcp-oauth.keys.json` al repositorio
- ⚠️ Mantén tus credenciales seguras
- ⚠️ Cada usuario debe tener sus propias credenciales OAuth