from mcp.server.fastmcp import FastMCP
import json
import sys
import os

# Agregar el directorio utils al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.env_loader import load_environment_variables

# Cargar variables de entorno
load_environment_variables()

# Crear servidor MCP
mcp = FastMCP(name="EconomIAssist", description="Asistente financiero personal")

# Datos simulados en memoria para pruebas
transacciones = []
saldo_inicial = 1000.0

@mcp.tool()
def echo(message: str) -> str:
    """Herramienta de prueba que hace eco de un mensaje"""
    return f"Echo: {message}"

@mcp.tool()
def registrar_transaccion(tipo: str, monto: float, descripcion: str, categoria: str = "General") -> dict:
    """
    Registra una transacción financiera.
    
    Args:
        tipo: "ingreso" o "gasto"
        monto: Cantidad de dinero (positiva)
        descripcion: Descripción de la transacción
        categoria: Categoría opcional (ej: "comida", "transporte")
    """
    if tipo not in ["ingreso", "gasto"]:
        return {"error": "Tipo debe ser 'ingreso' o 'gasto'"}
    
    if monto <= 0:
        return {"error": "El monto debe ser positivo"}
    
    transaccion = {
        "id": len(transacciones) + 1,
        "tipo": tipo,
        "monto": monto,
        "descripcion": descripcion,
        "categoria": categoria,
        "fecha": "2025-05-23"  # Fecha fija para el ejemplo
    }
    
    transacciones.append(transaccion)
    
    return {
        "status": "exitoso",
        "mensaje": f"Transacción registrada: {tipo} de ${monto} - {descripcion}",
        "transaccion": transaccion
    }

@mcp.tool()
def obtener_saldo() -> dict:
    """Obtiene el saldo actual calculado desde las transacciones"""
    total_ingresos = sum(t["monto"] for t in transacciones if t["tipo"] == "ingreso")
    total_gastos = sum(t["monto"] for t in transacciones if t["tipo"] == "gasto")
    saldo_actual = saldo_inicial + total_ingresos - total_gastos
    
    return {
        "saldo_inicial": saldo_inicial,
        "total_ingresos": total_ingresos,
        "total_gastos": total_gastos,
        "saldo_actual": saldo_actual,
        "numero_transacciones": len(transacciones)
    }

@mcp.tool()
def obtener_transacciones() -> dict:
    """Obtiene la lista de todas las transacciones"""
    return {
        "transacciones": transacciones,
        "total": len(transacciones)
    }

@mcp.resource("economiassist://resumen")
def resumen_financiero() -> str:
    """Proporciona un resumen completo del estado financiero"""
    saldo_info = obtener_saldo()
    resumen = f"""
RESUMEN FINANCIERO PERSONAL
===========================
Saldo inicial: ${saldo_info['saldo_inicial']}
Total ingresos: ${saldo_info['total_ingresos']}
Total gastos: ${saldo_info['total_gastos']}
SALDO ACTUAL: ${saldo_info['saldo_actual']}

Transacciones registradas: {saldo_info['numero_transacciones']}
"""
    
    if transacciones:
        resumen += "\nÚltimas transacciones:\n"
        for t in transacciones[-3:]:  # Últimas 3 transacciones
            resumen += f"- {t['tipo'].upper()}: ${t['monto']} - {t['descripcion']} ({t['categoria']})\n"
    
    return resumen

if __name__ == "__main__":
    # Ejecutar el servidor
    print("🚀 Iniciando servidor MCP EconomIAssist...")
    print("💡 Herramientas disponibles:")
    print("   - echo: Prueba de conectividad")
    print("   - registrar_transaccion: Registra ingresos y gastos")
    print("   - obtener_saldo: Consulta saldo actual")
    print("   - obtener_transacciones: Lista todas las transacciones")
    print("📊 Recursos disponibles:")
    print("   - economiassist://resumen: Resumen financiero completo")
    print("")
    mcp.run()