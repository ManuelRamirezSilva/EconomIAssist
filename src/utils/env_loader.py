import os
from pathlib import Path
from dotenv import load_dotenv

def load_environment_variables():
    """
    Carga variables de entorno desde el archivo .env en la raíz del proyecto.
    Debe llamarse al inicio de la aplicación.
    """
    # Busca el archivo .env en la raíz del proyecto (2 niveles arriba)
    env_path = Path(__file__).parents[2] / '.env'
    
    # Carga las variables desde .env
    load_dotenv(dotenv_path=env_path)

    use_azure = bool(os.getenv("AZURE_OPENAI_API_BASE"))
    if use_azure:
        import openai
        openai.api_type = "azure"
        openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
        openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        # Para usar el deployment por defecto en librerías que lo pidan:
        os.environ["OPENAI_API_KEY"] = openai.api_key

    required_keys = []
    if not use_azure:
        required_keys.append('OPENAI_API_KEY')

    missing = [k for k in required_keys if not os.getenv(k)]
    if missing:
        print(f"⚠️ Advertencia: Faltan: {', '.join(missing)}.")
    else:
        print("✅ Variables de entorno cargadas correctamente")
    
    return {key: os.getenv(key) for key in required_keys}

def get_env_var(key, default=None):
    """
    Obtiene una variable de entorno específica.
    Args:
        key: Nombre de la variable de entorno.
        default: Valor por defecto si la variable no existe.
    Returns:
        El valor de la variable de entorno o el valor por defecto.
    """
    return os.getenv(key, default)