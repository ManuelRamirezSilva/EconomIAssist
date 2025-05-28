#!/usr/bin/env python3
"""
Sistema de Registro MCP - Descubrimiento y Gestión Automática de Servidores
Hace que agregar nuevos servidores MCP sea trivial y declarativo
"""

import os
import json
import yaml
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
import structlog

logger = structlog.get_logger()

@dataclass
class MCPServerSpec:
    """Especificación completa de un servidor MCP"""
    name: str
    description: str
    command: List[str]
    env_vars: Dict[str, str] = field(default_factory=dict)
    required_env_keys: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    priority: int = 1
    auto_connect: bool = True
    health_check: Optional[Callable] = None
    
    def is_available(self) -> bool:
        """Verifica si el servidor puede conectarse (todas las env vars están disponibles)"""
        for key in self.required_env_keys:
            if not os.getenv(key):
                return False
        return True
    
    def get_runtime_env(self) -> Dict[str, str]:
        """Obtiene variables de entorno en tiempo de ejecución"""
        runtime_env = {}
        for key, value in self.env_vars.items():
            if value.startswith("$"):
                # Variable de entorno dinámica
                env_key = value[1:]  # Remover $
                runtime_env[key] = os.getenv(env_key, "")
            else:
                runtime_env[key] = value
        return runtime_env

class MCPServerRegistry:
    """Registro centralizado de servidores MCP con descubrimiento automático"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.servers: Dict[str, MCPServerSpec] = {}
        self.config_path = config_path or self._get_default_config_path()
        self._load_builtin_servers()
        self._load_config_file()
    
    def _get_default_config_path(self) -> str:
        """Obtiene la ruta por defecto del archivo de configuración"""
        return os.path.join(os.path.dirname(__file__), "..", "..", "config", "mcp_servers.yaml")
    
    def _load_builtin_servers(self):
        """Carga servidores MCP integrados"""
        
        # 🌐 Tavily Web Search
        self.register_server(MCPServerSpec(
            name="tavily",
            description="Búsqueda web inteligente con Tavily AI",
            command=["npx", "tavily-mcp"],
            env_vars={"TAVILY_API_KEY": "$TAVILY_API_KEY"},
            required_env_keys=["TAVILY_API_KEY"],
            capabilities=["web_search", "real_time_data"],
            priority=10
        ))
        
        # 💰 Servidor Financiero (Google Sheets)
        self.register_server(MCPServerSpec(
            name="financial",
            description="Gestión financiera con Google Sheets",
            command=["python", "-m", "mcp_servers.financial"],
            env_vars={
                "GOOGLE_SHEETS_API_KEY": "$GOOGLE_SHEETS_API_KEY",
                "SPREADSHEET_ID": "$FINANCIAL_SPREADSHEET_ID"
            },
            required_env_keys=["GOOGLE_SHEETS_API_KEY", "FINANCIAL_SPREADSHEET_ID"],
            capabilities=["financial_data", "expense_tracking", "income_logging"],
            priority=20
        ))
        
        # 📅 Google Calendar
        self.register_server(MCPServerSpec(
            name="calendar",
            description="Gestión de eventos y recordatorios",
            command=["python", "-m", "mcp_servers.calendar"],
            env_vars={
                "GOOGLE_CALENDAR_API_KEY": "$GOOGLE_CALENDAR_API_KEY",
                "CALENDAR_ID": "$GOOGLE_CALENDAR_ID"
            },
            required_env_keys=["GOOGLE_CALENDAR_API_KEY"],
            capabilities=["calendar_events", "reminders", "scheduling"],
            priority=15
        ))
        
        # 🏦 BCRA (Banco Central República Argentina)
        self.register_server(MCPServerSpec(
            name="bcra",
            description="Datos macroeconómicos del BCRA",
            command=["npx", "bcra-mcp"],
            env_vars={},  # API pública del BCRA
            required_env_keys=[],
            capabilities=["macroeconomic_data", "exchange_rates", "inflation"],
            priority=5,
            auto_connect=False  # Conectar solo cuando se necesite
        ))
        
        # 📊 Análisis de Mercados
        self.register_server(MCPServerSpec(
            name="markets",
            description="Análisis de mercados financieros",
            command=["python", "-m", "mcp_servers.markets"],
            env_vars={"ALPHA_VANTAGE_KEY": "$ALPHA_VANTAGE_API_KEY"},
            required_env_keys=["ALPHA_VANTAGE_API_KEY"],
            capabilities=["stock_data", "crypto_prices", "market_analysis"],
            priority=8,
            auto_connect=False
        ))
    
    def _load_config_file(self):
        """Carga servidores desde archivo de configuración YAML"""
        config_file = Path(self.config_path)
        if not config_file.exists():
            logger.info(f"📄 Archivo de configuración no encontrado: {config_file}")
            self._create_default_config()
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            servers_config = config.get('mcp_servers', {})
            for name, spec in servers_config.items():
                server_spec = MCPServerSpec(
                    name=name,
                    description=spec.get('description', ''),
                    command=spec.get('command', []),
                    env_vars=spec.get('env_vars', {}),
                    required_env_keys=spec.get('required_env_keys', []),
                    capabilities=spec.get('capabilities', []),
                    priority=spec.get('priority', 1),
                    auto_connect=spec.get('auto_connect', True)
                )
                self.register_server(server_spec)
                
            logger.info(f"📄 Configuración cargada desde: {config_file}")
                
        except Exception as e:
            logger.error(f"❌ Error cargando configuración: {e}")
    
    def _create_default_config(self):
        """Crea un archivo de configuración por defecto"""
        config_dir = Path(self.config_path).parent
        config_dir.mkdir(parents=True, exist_ok=True)
        
        default_config = {
            'mcp_servers': {
                'custom_server_example': {
                    'description': 'Ejemplo de servidor personalizado',
                    'command': ['python', '-m', 'my_custom_mcp_server'],
                    'env_vars': {'API_KEY': '$MY_API_KEY'},
                    'required_env_keys': ['MY_API_KEY'],
                    'capabilities': ['custom_capability'],
                    'priority': 1,
                    'auto_connect': False
                }
            }
        }
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"📄 Archivo de configuración creado: {self.config_path}")
        except Exception as e:
            logger.error(f"❌ Error creando configuración: {e}")
    
    def register_server(self, spec: MCPServerSpec):
        """Registra un nuevo servidor MCP"""
        self.servers[spec.name] = spec
        logger.debug(f"📝 Servidor registrado: {spec.name}")
    
    def discover_available_servers(self) -> Dict[str, MCPServerSpec]:
        """Descubre qué servidores están disponibles para conectar"""
        available = {}
        
        for name, spec in self.servers.items():
            if spec.is_available():
                available[name] = spec
                logger.info(f"✅ Servidor disponible: {name} - {spec.description}")
            else:
                missing_keys = [key for key in spec.required_env_keys if not os.getenv(key)]
                logger.warning(f"⚠️ Servidor no disponible: {name} (faltan: {missing_keys})")
        
        return available
    
    def get_auto_connect_servers(self) -> Dict[str, MCPServerSpec]:
        """Obtiene servidores que deben conectarse automáticamente"""
        available = self.discover_available_servers()
        auto_connect = {
            name: spec for name, spec in available.items() 
            if spec.auto_connect
        }
        return auto_connect
    
    def get_servers_by_capability(self, capability: str) -> Dict[str, MCPServerSpec]:
        """Encuentra servidores que tienen una capacidad específica"""
        available = self.discover_available_servers()
        matching = {
            name: spec for name, spec in available.items()
            if capability in spec.capabilities
        }
        return matching
    
    def get_server_priorities(self) -> List[str]:
        """Obtiene nombres de servidores ordenados por prioridad (mayor a menor)"""
        available = self.discover_available_servers()
        sorted_servers = sorted(
            available.items(), 
            key=lambda x: x[1].priority, 
            reverse=True
        )
        return [name for name, _ in sorted_servers]
    
    def export_config(self, path: str):
        """Exporta la configuración actual a un archivo YAML"""
        config = {'mcp_servers': {}}
        
        for name, spec in self.servers.items():
            if name not in ['tavily', 'financial', 'calendar', 'bcra', 'markets']:  # Excluir builtin
                config['mcp_servers'][name] = {
                    'description': spec.description,
                    'command': spec.command,
                    'env_vars': spec.env_vars,
                    'required_env_keys': spec.required_env_keys,
                    'capabilities': spec.capabilities,
                    'priority': spec.priority,
                    'auto_connect': spec.auto_connect
                }
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"📄 Configuración exportada a: {path}")

# Instancia global del registro
_registry = None

def get_mcp_registry() -> MCPServerRegistry:
    """Obtiene la instancia global del registro MCP"""
    global _registry
    if _registry is None:
        _registry = MCPServerRegistry()
    return _registry

def register_custom_server(spec: MCPServerSpec):
    """Función de conveniencia para registrar servidores personalizados"""
    registry = get_mcp_registry()
    registry.register_server(spec)

# Ejemplo de uso para desarrolladores
if __name__ == "__main__":
    # Ejemplo: registrar un servidor personalizado
    custom_spec = MCPServerSpec(
        name="mi_servidor",
        description="Mi servidor MCP personalizado",
        command=["python", "mi_servidor_mcp.py"],
        env_vars={"MI_API_KEY": "$MI_API_KEY"},
        required_env_keys=["MI_API_KEY"],
        capabilities=["mi_capacidad"],
        priority=5
    )
    
    register_custom_server(custom_spec)
    
    # Mostrar servidores disponibles
    registry = get_mcp_registry()
    available = registry.discover_available_servers()
    
    print("🔍 Servidores MCP Disponibles:")
    for name, spec in available.items():
        print(f"  ✅ {name}: {spec.description}")
        print(f"     📋 Capacidades: {', '.join(spec.capabilities)}")