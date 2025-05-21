from mcp.server.fastmcp import FastMCP, Context
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

# from fake_database import Database # Replace with your actual DB type or remove

# @dataclass
# class AppContext:
# db: Database

# @asynccontextmanager
# async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
# """Manage application lifecycle with type-safe context"""
# # Initialize on startup
# db = await Database.connect()
# try:
# yield AppContext(db=db)
# finally:
# # Cleanup on shutdown
# await db.disconnect()

# Create an MCP server instance
# Pass lifespan to server if you have one: lifespan=app_lifespan
mcp = FastMCP(name="EconomIAssistServer", description="Servidor MCP para EconomIAssist")

# Example Tool (to be replaced or expanded)
@mcp.tool()
def example_tool(query: str) -> str:
    """An example tool that echoes the input."""
    return f"Echo from EconomIAssist: {query}"

# Example Resource (to be replaced or expanded)
@mcp.resource("economiassist://example/info")
def get_example_info() -> dict:
    """An example resource providing static information."""
    return {"version": "0.1.0", "status": "development"}

# --- EconomIAssist Specific Tools ---

@mcp.tool()
def registrar_transaccion(tipo: str, monto: float, descripcion: str, ctx: Context | None = None) -> dict:
    """
    Registra una transacción financiera (ingreso o egreso).
    Args:
        tipo: "ingreso" o "egreso".
        monto: El monto de la transacción.
        descripcion: Una breve descripción de la transacción.
        ctx: El contexto MCP (opcional por ahora).
    Returns:
        Un diccionario confirmando la transacción.
    """
    # En una implementación real, esto interactuaría con Google Sheets o una BD.
    # ctx.info(f"Registrando transacción: {tipo} de {monto} ({descripcion})") # Ejemplo si usaras ctx
    print(f"Transacción registrada (simulado): {tipo} de {monto} - {descripcion}")
    return {"status": "exito", "mensaje": f"Transacción '{descripcion}' de tipo '{tipo}' por {monto} registrada."}

# --- EconomIAssist Specific Resources ---

@mcp.resource("economiassist://finanzas/resumen")
def obtener_info_financiera() -> dict:
    """
    Proporciona un resumen financiero básico.
    Returns:
        Un diccionario con información financiera de ejemplo.
    """
    # En una implementación real, esto obtendría datos de Google Sheets.
    # data, mime_type = await ctx.read_resource("file:///path/to/financial_summary.json") # Ejemplo si usaras ctx
    print("Obteniendo resumen financiero (simulado)")
    return {
        "saldo_actual": 1250.75,
        "total_ingresos_mes": 500.00,
        "total_egresos_mes": 250.25,
        "proxima_fecha_pago": "2025-06-01"
    }

if __name__ == "__main__":
    # To run in development mode with MCP Inspector:
    # mcp dev /home/agustin/Documentos/4to/nlp/EconomIAssist/src/mcp_server/server.py
    #
    # To run directly (e.g., for custom deployments):
    mcp.run()