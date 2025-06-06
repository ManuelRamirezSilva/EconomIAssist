FROM python:3.12-slim

WORKDIR /app

# Copiar requirements y instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY src/ ./src/
COPY config/ ./config/

# Crear directorio para datos persistentes
RUN mkdir -p /app/data

# Exponer puerto si es necesario (para APIs futuras)
EXPOSE 8000

# Comando por defecto
CMD ["python", "src/agent/conversational_agent.py"]