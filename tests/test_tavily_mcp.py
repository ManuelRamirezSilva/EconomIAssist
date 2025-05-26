#!/usr/bin/env python3
"""
Ejemplo de integración MCP (Tavily) + Azure OpenAI function calling - NO USA PYTEST
"""
import os
import asyncio
from dotenv import load_dotenv
from openai import AzureOpenAI
import json
import inspect

# Importa el cliente MCP real
from src.agent.mcp_client import MCPManager

load_dotenv()

async def main():
    # 1. Conectar a Tavily MCP y descubrir herramientas
    mcp_manager = MCPManager()
    success = await mcp_manager.connect_tavily_server()
    if not success:
        print("❌ No se pudo conectar a Tavily MCP")
        return
    tools_by_server = await mcp_manager.get_available_tools()
    tavily_tools = mcp_manager.connections["tavily"].tools
    if not tavily_tools:
        print("❌ No se encontraron herramientas en Tavily MCP")
        return

    # 2. Convertir herramientas MCP a formato OpenAI function calling
    openai_tools = []
    for tool in tavily_tools.values():
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema or {}
            }
        })

    # 3. Configurar cliente Azure OpenAI
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_base = os.getenv("AZURE_OPENAI_API_BASE")
    azure_version = os.getenv("AZURE_OPENAI_API_VERSION")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    if not azure_key or not azure_base or not azure_version or not deployment_name:
        print("Error: Debes configurar AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_BASE, AZURE_OPENAI_API_VERSION y AZURE_OPENAI_DEPLOYMENT_NAME en .env")
        return
    client = AzureOpenAI(
        azure_endpoint=azure_base,
        api_key=azure_key,
        api_version=azure_version
    )

    # 4. Mensaje de prueba
    messages = [
        {"role": "system", "content": "Eres un asistente que puede realizar búsquedas web usando herramientas MCP."},
        {"role": "user", "content": "¿Cuál es la tasa de interés actual?"}
    ]

    print("Enviando petición a GPT-4o-mini con tools (function calling)...")
    response = client.chat.completions.create(
        model=deployment_name,
        messages=messages,
        tools=openai_tools,
        temperature=0
    )

    choice = response.choices[0]
    msg = choice.message
    if hasattr(msg, "tool_calls") and msg.tool_calls:
        # 5. El modelo solicita llamar una función/tool
        tool_call = msg.tool_calls[0]
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)
        print(f"🔧 El modelo solicita llamar la tool: {tool_name} con argumentos: {tool_args}")
        # 6. Ejecutar la tool real en Tavily MCP
        result = await mcp_manager.connections["tavily"].call_tool(tool_name, tool_args)
        print(f"📡 Respuesta de la tool MCP: {result}")
        # 7. Enviar la respuesta de la tool como mensaje de tool al modelo (simulación)
        tool_message = {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_name,
            "content": json.dumps(result)
        }
        messages.append({"role": "assistant", "content": msg.content, "tool_calls": [
            {"id": tool_call.id, "function": {"name": tool_name, "arguments": tool_call.function.arguments}, "type": "function"}
        ]})
        messages.append(tool_message)
        # 8. Segunda llamada: el modelo responde al usuario usando el resultado de la tool
        response2 = client.chat.completions.create(
            model=deployment_name,
            messages=messages,
            temperature=0
        )
        final_content = response2.choices[0].message.content
        print("\n🤖 Respuesta final del modelo:")
        print(final_content)
    else:
        print("\n🤖 Respuesta del modelo:")
        print(msg.content)

    await mcp_manager.disconnect_all()

if __name__ == "__main__":
    asyncio.run(main())
