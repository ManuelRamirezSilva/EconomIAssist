import streamlit as st
import pandas as pd
import os
import re
import json
from datetime import datetime

# Configuración inicial de la aplicación  
st.set_page_config(page_title="Dashboard de Logs y Métricas", layout="wide")

# Add custom CSS for better JSON display
st.markdown("""
<style>
.log-detail-modal {
    background: #f0f2f6;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 15px;
    margin: 10px 0;
    max-height: 400px;
    overflow-y: auto;
}
.log-section {
    background: #ffffff;
    border-left: 4px solid #1f77b4;
    padding: 8px 12px;
    margin: 5px 0;
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 12px;
}
.json-section {
    background: #f8f9fa;
    border-left: 4px solid #28a745;
    padding: 12px;
    margin: 5px 0;
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 12px;
}
.log-key {
    color: #d73027;
    font-weight: bold;
}
.log-value {
    color: #2166ac;
}
.json-key {
    color: #6f42c1;
    font-weight: bold;
}
.json-value {
    color: #28a745;
}
.nested-json {
    margin-left: 15px;
    border-left: 2px solid #dee2e6;
    padding-left: 10px;
}
</style>
""", unsafe_allow_html=True)

def format_timestamp(timestamp):
    """Format timestamp to replace T with spaces and handle timezone info"""
    if not timestamp:
        return ""
    
    # Replace T with spaces for better readability
    formatted = timestamp.replace('T', '   ')
    
    # Remove timezone info (Z, +XX:XX, -XX:XX) as they might be irrelevant for local analysis
    formatted = re.sub(r'[+-]\d{2}:\d{2}$', '', formatted)
    formatted = re.sub(r'Z$', '', formatted)
    
    return formatted

def format_json_value(value, max_length=100):
    """Format JSON values for display, handling nested structures"""
    if isinstance(value, dict):
        return json.dumps(value, indent=2)
    elif isinstance(value, list):
        return json.dumps(value, indent=2)
    elif isinstance(value, str) and len(value) > max_length:
        return value[:max_length] + "..."
    else:
        return str(value)

def parse_log_sections(log_text):
    """Enhanced log text parsing with better JSON handling"""
    if not log_text:
        return []
    
    sections = []
    
    # First try to parse the entire text as JSON
    try:
        json_data = json.loads(log_text)
        sections.append({
            "type": "complete_json", 
            "data": json_data,
            "formatted": json.dumps(json_data, indent=2, ensure_ascii=False)
        })
        return sections
    except:
        pass
    
    # Try to find JSON objects within the text
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    json_matches = re.findall(json_pattern, log_text)
    
    remaining_text = log_text
    
    for json_match in json_matches:
        try:
            json_obj = json.loads(json_match)
            sections.append({
                "type": "embedded_json",
                "data": json_obj,
                "formatted": json.dumps(json_obj, indent=2, ensure_ascii=False),
                "original": json_match
            })
            # Remove the JSON from remaining text
            remaining_text = remaining_text.replace(json_match, '', 1)
        except:
            continue
    
    # Parse key-value pairs from remaining text
    kv_patterns = [
        r'(\w+)\s*=\s*"([^"]*)"',  # key="value"
        r'(\w+)\s*=\s*\'([^\']*)\'',  # key='value'  
        r'(\w+)\s*=\s*([^\s,;]+)',  # key=value
        r'(\w+)\s*:\s*"([^"]*)"',  # key:"value"
        r'(\w+)\s*:\s*\'([^\']*)\'',  # key:'value'
        r'(\w+)\s*:\s*([^\s,;]+)',  # key:value
        r'\[(\w+)\s*=\s*([^\]]+)\]',  # [key=value]
    ]
    
    for pattern in kv_patterns:
        matches = re.findall(pattern, remaining_text)
        for key, value in matches:
            sections.append({"type": "key_value", "key": key, "value": value})
            # Remove matched pattern from remaining text
            remaining_text = re.sub(pattern, '', remaining_text, count=1)
    
    # Add any remaining text as free text
    remaining_text = remaining_text.strip()
    remaining_text = re.sub(r'[,;:\s]+', ' ', remaining_text).strip()
    if remaining_text and len(remaining_text) > 3:  # Only add if meaningful text remains
        sections.append({"type": "free_text", "key": "Additional Info", "value": remaining_text})
    
    return sections

def display_json_section(json_data, title="JSON Data"):
    """Display JSON data with proper formatting and collapsible structure"""
    st.markdown(f"**{title}:**")
    
    # Create tabs for different views of JSON
    tab1, tab2 = st.tabs(["🎨 Formatted View", "📝 Raw JSON"])
    
    with tab1:
        # Display as formatted key-value pairs
        def render_json_tree(data, level=0):
            indent = "  " * level
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, (dict, list)):
                        st.markdown(f"{indent}**{key}:**")
                        render_json_tree(value, level + 1)
                    else:
                        formatted_value = format_json_value(value)
                        st.markdown(f"{indent}**{key}:** `{formatted_value}`")
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    st.markdown(f"{indent}**[{i}]:**")
                    render_json_tree(item, level + 1)
            else:
                st.markdown(f"{indent}`{format_json_value(data)}`")
        
        render_json_tree(json_data)
    
    with tab2:
        # Display raw JSON with syntax highlighting
        formatted_json = json.dumps(json_data, indent=2, ensure_ascii=False)
        st.code(formatted_json, language='json')

# Función mejorada para parsear logs
def parse_log_line(line):
    """
    Parse a log line into timestamp, event, and other components.
    Looks for actual "event" key in the log data.
    """
    line = line.strip()
    if not line:
        return {"timestamp": "", "event": "", "other": ""}
    
    # Common timestamp patterns
    timestamp_patterns = [
        # ISO format: 2024-01-15T10:30:45.123Z or 2024-01-15 10:30:45
        r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d{3})?(?:Z|[+-]\d{2}:\d{2})?)',
        # Common log format: [2024-01-15 10:30:45]
        r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]',
        # Syslog format: Jan 15 10:30:45
        r'([A-Za-z]{3} \d{1,2} \d{2}:\d{2}:\d{2})',
        # Simple time: 10:30:45
        r'(\d{2}:\d{2}:\d{2})',
        # Unix timestamp: 1642248645
        r'(\d{10})',
    ]
    
    timestamp = ""
    remaining_line = line
    
    # Try to extract timestamp
    for pattern in timestamp_patterns:
        match = re.search(pattern, line)
        if match:
            timestamp = match.group(1)
            # Remove timestamp from line
            remaining_line = re.sub(pattern, "", line).strip()
            # Clean up common separators left behind
            remaining_line = re.sub(r'^[-\s\[\]]+', '', remaining_line).strip()
            break
    
    if not timestamp:
        # If no timestamp found, check if line starts with a timestamp-like string
        parts = line.split()
        if parts and re.match(r'\d+', parts[0]):
            timestamp = parts[0]
            remaining_line = ' '.join(parts[1:])
    
    # Extract event by looking for "event" key in the log
    event = ""
    other = remaining_line
    
    if remaining_line:
        # Look for "event" key patterns in the remaining line
        event_patterns = [
            # Pattern 1: event="value" or event='value'
            r'event\s*=\s*["\']([^"\']+)["\']',
            # Pattern 2: event=value (without quotes, up to space or comma)
            r'event\s*=\s*([^\s,]+)',
            # Pattern 3: "event": "value" (JSON-like)
            r'"event"\s*:\s*"([^"]+)"',
            # Pattern 4: 'event': 'value' (JSON-like with single quotes)
            r"'event'\s*:\s*'([^']+)'",
            # Pattern 5: event: value (colon separator)
            r'event\s*:\s*([^\s,]+)',
            # Pattern 6: [event=value] or [event="value"]
            r'\[event\s*=\s*["\']?([^"\'\]]+)["\']?\]',
            # Pattern 7: key-value with different separators
            r'event\s*[-=:]\s*["\']?([^"\';\s,]+)["\']?',
        ]
        
        for pattern in event_patterns:
            match = re.search(pattern, remaining_line, re.IGNORECASE)
            if match:
                event = match.group(1)
                # Remove the matched event key-value pair from remaining_line
                other = re.sub(pattern, "", remaining_line, flags=re.IGNORECASE).strip()
                # Clean up common separators left behind
                other = re.sub(r'^[-:\s,;]+|[-:\s,;]+$', '', other).strip()
                break
        
        # If no event key found, try to extract common log levels as events
        if not event:
            log_level_patterns = [
                r'\b(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|TRACE|CRITICAL)\b',
                r'\[(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|TRACE|CRITICAL)\]',
            ]
            
            for pattern in log_level_patterns:
                match = re.search(pattern, remaining_line, re.IGNORECASE)
                if match:
                    event = match.group(1).upper()
                    # Remove the matched log level from remaining_line
                    other = re.sub(pattern, "", remaining_line, flags=re.IGNORECASE).strip()
                    break
        
        # If still no event found, leave event empty and keep all remaining text in other
        if not event:
            event = ""
            other = remaining_line
    
    return {
        "timestamp": format_timestamp(timestamp),
        "event": event,
        "other": other
    }

# Función para cargar los logs desde la carpeta
@st.cache_data
def cargar_logs():
    logs = []
    carpeta_logs = "logs"
    
    if not os.path.exists(carpeta_logs):
        st.warning(f"La carpeta '{carpeta_logs}' no existe.")
        return pd.DataFrame(columns=["timestamp", "event", "other", "file", "original_log", "line_number"])
    
    for archivo in os.listdir(carpeta_logs):
        if archivo.endswith(".log"):
            ruta = os.path.join(carpeta_logs, archivo)
            try:
                with open(ruta, "r", encoding='utf-8') as f:
                    contenido = f.readlines()
                    for line_num, linea in enumerate(contenido, 1):
                        parsed_log = parse_log_line(linea)
                        parsed_log["file"] = archivo  # Add source file info
                        parsed_log["original_log"] = linea.strip()  # Keep original log
                        parsed_log["line_number"] = line_num  # Add line number for reference
                        logs.append(parsed_log)
            except Exception as e:
                st.error(f"Error leyendo archivo {archivo}: {str(e)}")
    
    return pd.DataFrame(logs)

# Función para validar y limpiar timestamps
def clean_timestamps(df):
    """Clean and standardize timestamps in the dataframe"""
    if df.empty:
        return df
    
    df = df.copy()
    
    # Try to convert timestamps to datetime for better sorting/filtering
    def safe_timestamp_convert(ts):
        if not ts or pd.isna(ts):
            return None
        try:
            # Try different datetime formats
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%fZ']:
                try:
                    return pd.to_datetime(ts, format=fmt)
                except:
                    continue
            # Try pandas' general parsing
            return pd.to_datetime(ts)
        except:
            return ts  # Return original if can't parse
    
    df['timestamp_parsed'] = df['timestamp'].apply(safe_timestamp_convert)
    return df

# Cargar los logs
st.title("Dashboard de Logs y Métricas")
st.markdown("Este dashboard parsea automáticamente los logs en componentes estructurados: **timestamp**, **event**, y **other**.")

logs_df = cargar_logs()

# Limpiar timestamps
if not logs_df.empty:
    logs_df = clean_timestamps(logs_df)

# Visualización de logs en tabla
st.subheader("Logs Parseados")

if not logs_df.empty:
    # Selector de archivo
    archivos_disponibles = ["Todos los archivos"] + sorted(logs_df['file'].unique().tolist())
    archivo_seleccionado = st.selectbox("Seleccionar archivo:", archivos_disponibles)
    
    # Filtrar por archivo si no es "Todos"
    if archivo_seleccionado != "Todos los archivos":
        logs_por_archivo = logs_df[logs_df['file'] == archivo_seleccionado]
    else:
        logs_por_archivo = logs_df
    
    # Filtros adicionales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_evento = st.text_input("Filtrar por evento")
    with col2:
        filtro_timestamp = st.text_input("Filtrar por timestamp")
    with col3:
        filtro_otros = st.text_input("Filtrar por contenido en 'other'")
    
    # Aplicar filtros
    logs_filtrados = logs_por_archivo
    if filtro_evento:
        logs_filtrados = logs_filtrados[logs_filtrados["event"].str.contains(filtro_evento, case=False, na=False)]
    if filtro_timestamp:
        logs_filtrados = logs_filtrados[logs_filtrados["timestamp"].str.contains(filtro_timestamp, case=False, na=False)]
    if filtro_otros:
        logs_filtrados = logs_filtrados[logs_filtrados["other"].str.contains(filtro_otros, case=False, na=False)]
    
    # Mostrar estadísticas
    if archivo_seleccionado != "Todos los archivos":
        st.write(f"**Archivo:** {archivo_seleccionado} | **Logs en archivo:** {len(logs_por_archivo)} | **Logs filtrados:** {len(logs_filtrados)}")
    else:
        st.write(f"**Total de logs:** {len(logs_df)} | **Logs filtrados:** {len(logs_filtrados)}")
    
    # Crear columnas para mostrar
    if not logs_filtrados.empty:
        # Reordenar columnas para mejor visualización
        display_columns = ["timestamp", "event", "other", "file", "line_number"]
        display_df = logs_filtrados[display_columns].copy()
        
        # Truncate 'other' column for table display
        display_df['other_preview'] = display_df['other'].apply(
            lambda x: x[:80] + "..." if isinstance(x, str) and len(x) > 80 else x
        )
        display_df = display_df.drop('other', axis=1)
        display_df = display_df.rename(columns={'other_preview': 'other'})
        
        # Mostrar dataframe sin selección de filas
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "line_number": st.column_config.NumberColumn("Línea", help="Número de línea en el archivo"),
                "file": st.column_config.TextColumn("Archivo", help="Archivo de origen"),
                "timestamp": st.column_config.TextColumn("Timestamp", help="Marca de tiempo extraída"),
                "event": st.column_config.TextColumn("Evento", help="Tipo de evento identificado"),
                "other": st.column_config.TextColumn("Otros", help="Información adicional del log")
            }
        )
    else:
        st.warning("No hay logs que coincidan con los filtros aplicados.")
        
    # Mostrar muestra de parsing
    if st.checkbox("Mostrar ejemplos de parsing"):
        st.subheader("Ejemplos de Parsing")
        sample_logs = [
            "2024-01-15 10:30:45 INFO User login successful - user_id: 12345, session: abc123",
            "[2024-01-15 11:20:30] ERROR Database connection failed: timeout after 30s",
            "Jan 15 12:45:22 server1 WARNING Disk space low on /var/log",
            "10:30:45 DEBUG Processing request for endpoint /api/users",
            "1642248645 FATAL System shutdown initiated by admin",
            '2024-01-15T10:30:45Z event="user_login" user_id=12345 status="success"',
            'INFO: Processing event="data_sync" source="database" records=150',
            '2024-01-15T10:30:45Z {"event": "user_action", "user_id": 12345, "action": "login", "metadata": {"ip": "192.168.1.1", "user_agent": "Mozilla/5.0"}}',
            '2024-01-15T10:30:45Z Processing request {"request_id": "abc123", "endpoint": "/api/users", "method": "GET", "response_time": 45}'
        ]
        
        for sample in sample_logs:
            parsed = parse_log_line(sample)
            st.write(f"**Original:** `{sample}`")
            st.write(f"**Parsed:** timestamp=`{parsed['timestamp']}`, event=`{parsed['event']}`, other=`{parsed['other']}`")
            
            # Show what the JSON parsing would extract
            if parsed['other']:
                sections = parse_log_sections(parsed['other'])
                json_sections = [s for s in sections if s['type'] in ['complete_json', 'embedded_json']]
                if json_sections:
                    st.success(f"✅ Se detectaría {len(json_sections)} estructura(s) JSON en este log")
                else:
                    st.info("ℹ️ No se detectan estructuras JSON en este log")
            st.write("---")

else:
    st.warning("No se encontraron logs para mostrar. Asegúrate de que existe la carpeta 'logs' con archivos .log")

# Análisis de logs
if not logs_df.empty:
    st.subheader("Análisis de Logs")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Eventos más comunes
        st.write("**Eventos más comunes:**")
        event_counts = logs_df['event'].value_counts().head(10)
        if not event_counts.empty:
            st.bar_chart(event_counts)
        else:
            st.write("No hay eventos para mostrar")
    
    with col2:
        # Distribución por archivo
        if 'file' in logs_df.columns:
            st.write("**Distribución por archivo:**")
            file_counts = logs_df['file'].value_counts()
            st.bar_chart(file_counts)

# Botones de acción
col1, col2 = st.columns(2)

with col1:
    if st.button("Recargar datos"):
        st.cache_data.clear()
        st.rerun()

with col2:
    if st.button("Exportar a CSV") and not logs_df.empty:
        # Choose what to export based on current view
        if 'logs_filtrados' in locals() and not logs_filtrados.empty:
            export_df = logs_filtrados[["timestamp", "event", "other", "file", "line_number", "original_log"]]
            if 'archivo_seleccionado' in locals() and archivo_seleccionado != "Todos los archivos":
                filename_suffix = f"_{archivo_seleccionado.replace('.log', '')}"
            else:
                filename_suffix = "_filtrados"
        else:
            export_df = logs_df[["line_number","timestamp", "event", "other", "file", "original_log"]]
            filename_suffix = "_todos_archivos"
        
        csv_data = export_df.to_csv(index=False)
        st.download_button(
            label="Descargar CSV",
            data=csv_data,
            file_name=f"logs_parseados{filename_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )