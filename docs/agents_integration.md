# Integración de OpenAI Agents en EconomIAssist

## 1. Configuración
- Edita `config/agent_config.yaml` con tu API key y endpoints MCP.

## 2. Uso Básico
```bash
python -c "from src.agent.openai_agent import run_agent; print(run_agent('Registra un ingreso de 100 pesos en \"comida\"'))"
```

## 3. Buenas prácticas
- Ajusta `tools` en la config según nuevos módulos MCP.
- Versiona el modelo LLM para reproducibilidad.

