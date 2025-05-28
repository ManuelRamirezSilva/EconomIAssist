#!/usr/bin/env python3
"""
Suite de pruebas simplificada para EconomIAssist
"""

import asyncio
import subprocess
import sys
import os
from pathlib import Path

def run_test_script(script_path: str, description: str) -> bool:
    """Ejecuta un script de prueba y retorna True si es exitoso"""
    print(f"\n{'='*50}")
    print(f"🧪 {description}")
    print(f"{'='*50}")
    
    try:
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, text=True, timeout=60)
        
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Warnings:")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} - EXITOSO")
            return True
        else:
            print(f"❌ {description} - FALLÓ")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def main():
    """Ejecuta todas las pruebas esenciales"""
    print("🚀 EconomIAssist - Suite de Pruebas Esencial")
    print("=" * 60)
    
    tests_dir = Path(__file__).parent
    results = {}
    
    # Pruebas esenciales
    test_cases = [
        (tests_dir / "test_azure_connection.py", "Conectividad Azure OpenAI"),
        (tests_dir / "test_openai_agents_sdk.py", "OpenAI Agents SDK"),
        (tests_dir / "test_tavily_mcp.py", "Integración MCP + Tavily"),
    ]
    
    # Ejecutar pruebas
    for script_path, description in test_cases:
        if script_path.exists():
            results[description] = run_test_script(str(script_path), description)
        else:
            print(f"⚠️ Archivo no encontrado: {script_path}")
            results[description] = False
    
    # Resumen final
    print(f"\n{'='*60}")
    print("📊 RESUMEN FINAL")
    print(f"{'='*60}")
    
    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)
    
    for test_name, success in results.items():
        status = "✅ EXITOSO" if success else "❌ FALLÓ"
        print(f"   {test_name:<25} {status}")
    
    print(f"\n🎯 Resultado: {passed_tests}/{total_tests} pruebas exitosas")
    
    if passed_tests == total_tests:
        print("🎉 ¡Todo funcionando perfectamente!")
        return 0
    elif passed_tests > 0:
        print("⚠️ Funcionalidad parcial disponible")
        return 1
    else:
        print("❌ Revisar configuración")
        return 2

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)