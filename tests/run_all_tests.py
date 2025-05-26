#!/usr/bin/env python3
"""
Script principal para ejecutar todas las pruebas del proyecto EconomIAssist
"""

import asyncio
import subprocess
import sys
import os
from pathlib import Path

def run_test_script(script_path: str, description: str) -> bool:
    """Ejecuta un script de prueba y retorna True si es exitoso"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, text=True, timeout=120)
        
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Warnings/Errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} - EXITOSO")
            return True
        else:
            print(f"❌ {description} - FALLÓ (código: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT (>120s)")
        return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

async def run_pytest_tests():
    """Ejecuta las pruebas con pytest"""
    print(f"\n{'='*60}")
    print(f"🧪 Ejecutando pruebas con pytest")
    print(f"{'='*60}")
    
    try:
        # Cambiar al directorio del proyecto
        project_root = Path(__file__).parent.parent
        os.chdir(project_root)
        
        # Ejecutar pytest con verbosidad
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_azure_integration.py", 
            "-v", "--tb=short"
        ], capture_output=True, text=True, timeout=300)
        
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Warnings/Errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ Pruebas pytest - EXITOSAS")
            return True
        else:
            print(f"❌ Pruebas pytest - FALLARON (código: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Pruebas pytest - TIMEOUT (>300s)")
        return False
    except Exception as e:
        print(f"❌ Pruebas pytest - ERROR: {e}")
        return False

def main():
    """Función principal para ejecutar todas las pruebas"""
    print("🚀 EconomIAssist - Suite de Pruebas Completa")
    print("=" * 70)
    print("🔧 Framework: OpenAI Agents SDK + Azure OpenAI GPT-4o-mini")
    print("🧪 Ejecutando verificaciones de funcionalidad...")
    
    tests_dir = Path(__file__).parent
    results = {}
    
    # Lista de pruebas a ejecutar
    test_cases = [
        (tests_dir / "test_azure_connection.py", "Conectividad Azure OpenAI"),
        (tests_dir / "test_openai_agents_sdk.py", "OpenAI Agents SDK"),
    ]
    
    # Ejecutar pruebas individuales
    for script_path, description in test_cases:
        if script_path.exists():
            results[description] = run_test_script(str(script_path), description)
        else:
            print(f"⚠️ Archivo de prueba no encontrado: {script_path}")
            results[description] = False
    
    # Ejecutar pruebas con pytest (si está disponible)
    try:
        pytest_result = asyncio.run(run_pytest_tests())
        results["Pruebas pytest"] = pytest_result
    except Exception as e:
        print(f"⚠️ No se pudo ejecutar pytest: {e}")
        results["Pruebas pytest"] = False
    
    # Mostrar resumen final
    print(f"\n{'='*70}")
    print("📊 RESUMEN DE PRUEBAS")
    print(f"{'='*70}")
    
    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)
    
    for test_name, success in results.items():
        status = "✅ EXITOSO" if success else "❌ FALLÓ"
        print(f"   {test_name:<30} {status}")
    
    print(f"\n🎯 Resultado final: {passed_tests}/{total_tests} pruebas exitosas")
    
    if passed_tests == total_tests:
        print("🎉 ¡Todas las pruebas pasaron! El agente está listo para usar.")
        return 0
    elif passed_tests > 0:
        print("⚠️ Algunas pruebas fallaron, pero hay funcionalidad básica.")
        return 1
    else:
        print("❌ Todas las pruebas fallaron. Revisar configuración.")
        return 2

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)