#!/usr/bin/env python3
"""
EconomIAssist Database Viewer
Visualizador único que accede directamente al volumen Docker de la base de datos
sin crear copias locales
"""

import sqlite3
import subprocess
import os
import tempfile
import sys
from datetime import datetime
from pathlib import Path

class DatabaseViewer:
    """Visor de base de datos que accede directamente al volumen Docker"""
    
    def __init__(self):
        self.container_name = "economyassist-kb"
        self.temp_db_path = None
        
    def get_live_database(self):
        """Obtiene acceso temporal a la base de datos en vivo"""
        try:
            # Verificar que el contenedor existe
            check_cmd = ["docker", "ps", "-a", "--filter", f"name={self.container_name}", "--format", "{{.Names}}"]
            result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if self.container_name not in result.stdout:
                print(f"❌ Contenedor '{self.container_name}' no encontrado")
                return None
            
            # Verificar si está corriendo
            running_cmd = ["docker", "ps", "--filter", f"name={self.container_name}", "--format", "{{.Names}}"]
            result = subprocess.run(running_cmd, capture_output=True, text=True)
            
            if self.container_name not in result.stdout:
                print(f"⚠️  Contenedor parado. ¿Iniciarlo? (y/N): ", end="")
                if input().lower() == 'y':
                    start_cmd = ["docker", "start", self.container_name]
                    result = subprocess.run(start_cmd, capture_output=True)
                    if result.returncode != 0:
                        print("❌ Error iniciando el contenedor")
                        return None
                    print("✅ Contenedor iniciado")
                else:
                    return None
            
            # Crear archivo temporal para acceder a la base de datos
            temp_dir = tempfile.mkdtemp()
            self.temp_db_path = os.path.join(temp_dir, "live_db.db")
            
            # Copiar la base de datos actual desde el contenedor
            copy_cmd = ["docker", "cp", f"{self.container_name}:/db/knowledgebase.db", self.temp_db_path]
            result = subprocess.run(copy_cmd, capture_output=True)
            
            if result.returncode == 0:
                return sqlite3.connect(self.temp_db_path)
            else:
                print(f"❌ Error accediendo a la base de datos: {result.stderr.decode()}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def cleanup(self):
        """Limpia archivos temporales"""
        if self.temp_db_path and os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
                os.rmdir(os.path.dirname(self.temp_db_path))
            except:
                pass
    
    def show_statistics(self, conn):
        """Muestra estadísticas generales"""
        cursor = conn.cursor()
        
        print("\n" + "="*60)
        print("📊 ESTADÍSTICAS DE LA BASE DE DATOS EN VIVO".center(60))
        print("="*60)
        
        # Total de memorias
        cursor.execute("SELECT COUNT(*) FROM memory_nodes")
        total_memories = cursor.fetchone()[0]
        
        # Importancia promedio
        cursor.execute("SELECT AVG(importance) FROM memory_nodes")
        avg_importance = cursor.fetchone()[0] or 0
        
        # Número de categorías
        cursor.execute("SELECT COUNT(DISTINCT topic_id) FROM memory_nodes")
        categories = cursor.fetchone()[0]
        
        # Última memoria
        cursor.execute("SELECT MAX(created) FROM memory_nodes")
        last_memory = cursor.fetchone()[0]
        
        print(f"\n📈 Resumen General:")
        print(f"   • Total de memorias: \033[92m{total_memories}\033[0m")
        print(f"   • Categorías únicas: \033[94m{categories}\033[0m")
        print(f"   • Importancia promedio: \033[93m{avg_importance:.2f}\033[0m")
        print(f"   • Última memoria: \033[96m{last_memory}\033[0m")
        print(f"   • Consultado: \033[95m{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\033[0m")
        
        # Estadísticas por categoría
        cursor.execute("""
            SELECT 
                t.name,
                COUNT(*) as count,
                AVG(m.importance) as avg_importance,
                MAX(m.created) as latest
            FROM memory_nodes m
            JOIN topics t ON m.topic_id = t.id
            GROUP BY t.name
            ORDER BY count DESC
        """)
        
        categories_data = cursor.fetchall()
        if categories_data:
            print(f"\n📋 Por Categoría:")
            for cat_name, count, avg_imp, latest in categories_data:
                try:
                    latest_date = datetime.fromisoformat(latest.replace('Z', '+00:00')).strftime('%d/%m/%Y')
                except:
                    latest_date = latest[:10] if latest else "N/A"
                
                print(f"   • \033[94m{cat_name:<20}\033[0m: {count} memorias, {avg_imp:.2f} importancia, {latest_date}")
    
    def show_memories_by_category(self, conn):
        """Muestra memorias filtradas por categoría"""
        cursor = conn.cursor()
        
        # Obtener categorías disponibles
        cursor.execute("SELECT DISTINCT t.name FROM topics t JOIN memory_nodes m ON t.id = m.topic_id ORDER BY t.name")
        categories = [row[0] for row in cursor.fetchall()]
        
        if not categories:
            print("❌ No hay categorías disponibles")
            return
        
        print("\n📂 Categorías disponibles:")
        for i, cat in enumerate(categories, 1):
            print(f"  {i}. {cat}")
        
        try:
            choice = int(input(f"\nSelecciona una categoría (1-{len(categories)}): "))
            if 1 <= choice <= len(categories):
                selected_category = categories[choice - 1]
                
                cursor.execute("""
                    SELECT 
                        m.content,
                        m.importance,
                        m.created,
                        t.name as topic
                    FROM memory_nodes m
                    JOIN topics t ON m.topic_id = t.id
                    WHERE t.name = ?
                    ORDER BY m.importance DESC, m.created DESC
                """, (selected_category,))
                
                memories = cursor.fetchall()
                self.display_memories(memories, f"Categoría: {selected_category}")
            else:
                print("❌ Opción no válida")
        except ValueError:
            print("❌ Por favor ingresa un número válido")
    
    def show_top_memories(self, conn, min_importance=0.7):
        """Muestra las memorias más importantes"""
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                m.content,
                m.importance,
                m.created,
                t.name as topic
            FROM memory_nodes m
            JOIN topics t ON m.topic_id = t.id
            WHERE m.importance >= ?
            ORDER BY m.importance DESC, m.created DESC
            LIMIT 15
        """, (min_importance,))
        
        memories = cursor.fetchall()
        self.display_memories(memories, f"Memorias Importantes (≥{min_importance})")
    
    def search_memories(self, conn):
        """Busca memorias por contenido"""
        search_term = input("\n🔍 Ingresa el término a buscar: ").strip()
        
        if not search_term:
            print("❌ Término de búsqueda vacío")
            return
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                m.content,
                m.importance,
                m.created,
                t.name as topic
            FROM memory_nodes m
            JOIN topics t ON m.topic_id = t.id
            WHERE m.content LIKE ?
            ORDER BY m.importance DESC, m.created DESC
        """, (f"%{search_term}%",))
        
        memories = cursor.fetchall()
        self.display_memories(memories, f"Búsqueda: '{search_term}'")
    
    def show_all_memories(self, conn):
        """Muestra todas las memorias"""
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                m.content,
                m.importance,
                m.created,
                t.name as topic
            FROM memory_nodes m
            JOIN topics t ON m.topic_id = t.id
            ORDER BY m.importance DESC, m.created DESC
        """)
        
        memories = cursor.fetchall()
        self.display_memories(memories, "Todas las Memorias")
    
    def display_memories(self, memories, title):
        """Muestra las memorias de forma estructurada"""
        if not memories:
            print(f"❌ No se encontraron memorias para: {title}")
            return
        
        print(f"\n" + "="*60)
        print(f"🧠 {title.upper()}".center(60))
        print("="*60)
        print(f"Se encontraron {len(memories)} memorias")
        
        for i, (content, importance, created, topic) in enumerate(memories, 1):
            # Color según importancia
            if importance >= 0.8:
                imp_color = "\033[92m"  # Verde
            elif importance >= 0.6:
                imp_color = "\033[93m"  # Amarillo
            else:
                imp_color = "\033[91m"  # Rojo
            
            # Formatear fecha
            try:
                date_obj = datetime.fromisoformat(created.replace('Z', '+00:00'))
                formatted_date = date_obj.strftime('%d/%m/%Y %H:%M')
            except:
                formatted_date = created[:16] if created else "N/A"
            
            print(f"\n\033[1m📋 Memoria #{i}\033[0m")
            print("┌─────────────────────────────────────────────────────────┐")
            print(f"│ \033[94m🏷️  {topic:<25}\033[0m {imp_color}⭐ {importance:.2f}\033[0m │")
            print("├─────────────────────────────────────────────────────────┤")
            
            # Dividir contenido en líneas
            content = content.replace('"', '').replace("'", "")
            words = content.split()
            lines = []
            current_line = ""
            
            for word in words:
                if len(current_line + word) <= 55:
                    current_line += word + " "
                else:
                    if current_line:
                        lines.append(current_line.strip())
                    current_line = word + " "
            if current_line:
                lines.append(current_line.strip())
            
            for line in lines:
                print(f"│ {line:<55} │")
            
            print("├─────────────────────────────────────────────────────────┤")
            print(f"│ \033[96m📅 {formatted_date}\033[0m{' ' * (55 - len(formatted_date))}│")
            print("└─────────────────────────────────────────────────────────┘")
            
            # Pausa cada 5 memorias
            if i % 5 == 0 and i < len(memories):
                resp = input(f"\n\033[96mPresiona ENTER para continuar (o 'q' para salir): \033[0m")
                if resp.lower() == 'q':
                    break
    
    def show_database_structure(self, conn):
        """Muestra la estructura completa de la base de datos"""
        cursor = conn.cursor()
        
        print("\n" + "="*70)
        print("🏗️  ESTRUCTURA COMPLETA DE LA BASE DE DATOS".center(70))
        print("="*70)
        
        try:
            # Obtener todas las tablas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            if not tables:
                print("❌ No se encontraron tablas en la base de datos")
                return
            
            print(f"\n📊 Base de datos contiene \033[92m{len(tables)}\033[0m tablas:")
            
            for i, table_name in enumerate(tables, 1):
                print(f"\n\033[1m┌─ 📋 TABLA #{i}: \033[94m{table_name.upper()}\033[0m")
                
                # Obtener información de las columnas
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                if columns:
                    print("├─ 🔧 ESTRUCTURA:")
                    for col_id, col_name, col_type, not_null, default_val, is_pk in columns:
                        # Iconos según tipo
                        type_icon = "🔑" if is_pk else "📝" if "TEXT" in col_type else "🔢" if "INT" in col_type else "📅" if "DATE" in col_type or "TIME" in col_type else "📄"
                        
                        # Formatear información adicional
                        extra_info = []
                        if is_pk:
                            extra_info.append("PK")
                        if not_null:
                            extra_info.append("NOT NULL")
                        if default_val is not None:
                            extra_info.append(f"DEFAULT: {default_val}")
                        
                        extra_str = f" ({', '.join(extra_info)})" if extra_info else ""
                        print(f"│  {type_icon} \033[93m{col_name:<20}\033[0m \033[96m{col_type:<15}\033[0m\033[90m{extra_str}\033[0m")
                
                # Obtener índices de la tabla
                cursor.execute(f"PRAGMA index_list({table_name})")
                indexes = cursor.fetchall()
                
                if indexes:
                    print("├─ 📇 ÍNDICES:")
                    for index_info in indexes:
                        # SQLite puede devolver diferentes números de columnas según la versión
                        idx_name = index_info[1]  # nombre del índice
                        unique = index_info[2] if len(index_info) > 2 else False  # único
                        unique_str = " (UNIQUE)" if unique else ""
                        print(f"│  🔍 \033[95m{idx_name}\033[0m\033[90m{unique_str}\033[0m")
                
                # Obtener claves foráneas
                cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                foreign_keys = cursor.fetchall()
                
                if foreign_keys:
                    print("├─ 🔗 CLAVES FORÁNEAS:")
                    for fk_id, seq, ref_table, from_col, to_col, on_update, on_delete, match in foreign_keys:
                        print(f"│  🔗 \033[93m{from_col}\033[0m → \033[94m{ref_table}.\033[93m{to_col}\033[0m")
                
                # Contar registros en la tabla
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    record_count = cursor.fetchone()[0]
                    print(f"├─ 📊 REGISTROS: \033[92m{record_count:,}\033[0m")
                except Exception as e:
                    print(f"├─ 📊 REGISTROS: \033[91mError: {str(e)}\033[0m")
                
                # Mostrar algunos datos de ejemplo (primeras 3 filas)
                try:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                    sample_rows = cursor.fetchall()
                    
                    if sample_rows:
                        print("└─ 👁️  DATOS DE EJEMPLO:")
                        
                        # Obtener nombres de columnas para mostrar los datos
                        col_names = [col[1] for col in columns]
                        
                        for j, row in enumerate(sample_rows, 1):
                            print(f"   📝 Registro {j}:")
                            for col_name, value in zip(col_names, row):
                                # Truncar valores largos
                                str_value = str(value)
                                if len(str_value) > 50:
                                    str_value = str_value[:47] + "..."
                                print(f"      • {col_name}: \033[96m{str_value}\033[0m")
                            if j < len(sample_rows):
                                print("      " + "─" * 30)
                    else:
                        print("└─ 👁️  DATOS DE EJEMPLO: \033[90m(tabla vacía)\033[0m")
                        
                except Exception as e:
                    print(f"└─ 👁️  DATOS DE EJEMPLO: \033[91mError: {str(e)}\033[0m")
                
                # Separador entre tablas
                if i < len(tables):
                    print("\n" + "─" * 70)
            
            # Mostrar relaciones entre tablas
            print(f"\n\033[1m🔗 RELACIONES ENTRE TABLAS:\033[0m")
            all_foreign_keys = []
            
            for table_name in tables:
                cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                fks = cursor.fetchall()
                for fk in fks:
                    all_foreign_keys.append((table_name, fk[2], fk[3], fk[4]))  # tabla_origen, tabla_destino, col_origen, col_destino
            
            if all_foreign_keys:
                for origen, destino, col_origen, col_destino in all_foreign_keys:
                    print(f"   \033[94m{origen}\033[0m.\033[93m{col_origen}\033[0m ──→ \033[94m{destino}\033[0m.\033[93m{col_destino}\033[0m")
            else:
                print("   \033[90m(No se encontraron relaciones de clave foránea)\033[0m")
            
            # Información de integridad
            print(f"\n\033[1m🛡️  INFORMACIÓN DE INTEGRIDAD:\033[0m")
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]
            
            if integrity_result == "ok":
                print("   ✅ Integridad de la base de datos: \033[92mOK\033[0m")
            else:
                print(f"   ❌ Problemas de integridad: \033[91m{integrity_result}\033[0m")
            
            # Información del archivo de base de datos
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            db_size_bytes = page_count * page_size
            db_size_mb = db_size_bytes / (1024 * 1024)
            
            print(f"   📁 Tamaño de la base de datos: \033[96m{db_size_mb:.2f} MB\033[0m ({page_count:,} páginas)")
            print(f"   📅 Consultado: \033[95m{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\033[0m")
            
        except Exception as e:
            print(f"❌ Error al obtener la estructura: {e}")
            import traceback
            traceback.print_exc()

    def run(self):
        """Ejecuta el visualizador interactivo"""
        print("\033[96m🤖 ECONOMISSIST - VISUALIZADOR DE BASE DE DATOS\033[0m")
        print("\033[96mAcceso directo a la base de datos en tiempo real\033[0m")
        
        # Obtener conexión a la base de datos en vivo
        conn = self.get_live_database()
        if not conn:
            return
        
        print("\n✅ Conectado a la base de datos en tiempo real")
        
        try:
            while True:
                print("\n" + "="*60)
                print("MENÚ PRINCIPAL".center(60))
                print("="*60)
                
                print("\nOpciones disponibles:")
                print("  \033[92m1.\033[0m Ver estadísticas generales")
                print("  \033[92m2.\033[0m Ver memorias más importantes")
                print("  \033[92m3.\033[0m Filtrar por categoría")
                print("  \033[92m4.\033[0m Buscar en contenido")
                print("  \033[92m5.\033[0m Ver todas las memorias")
                print("  \033[92m6.\033[0m Ver estructura de la base de datos")
                print("  \033[92m7.\033[0m Actualizar datos (reconectar)")
                print("  \033[91m0.\033[0m Salir")
                
                choice = input(f"\n\033[96mSelecciona una opción: \033[0m")
                
                if choice == '1':
                    self.show_statistics(conn)
                elif choice == '2':
                    self.show_top_memories(conn)
                elif choice == '3':
                    self.show_memories_by_category(conn)
                elif choice == '4':
                    self.search_memories(conn)
                elif choice == '5':
                    self.show_all_memories(conn)
                elif choice == '6':
                    self.show_database_structure(conn)
                elif choice == '7':
                    conn.close()
                    print("🔄 Actualizando conexión...")
                    conn = self.get_live_database()
                    if not conn:
                        break
                    print("✅ Datos actualizados")
                elif choice == '0':
                    print("\n👋 ¡Hasta luego!")
                    break
                else:
                    print("❌ Opción no válida")
                    
        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!")
        finally:
            conn.close()
            self.cleanup()

if __name__ == "__main__":
    viewer = DatabaseViewer()
    viewer.run()