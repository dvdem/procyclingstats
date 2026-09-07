from nicegui import ui, run
import polars as pl
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_PCS_ROOT = os.path.join(PROJECT_DIR, "procyclingstats")
if os.path.isdir(os.path.join(LOCAL_PCS_ROOT, "procyclingstats")) and LOCAL_PCS_ROOT not in sys.path:
    sys.path.insert(0, LOCAL_PCS_ROOT)

from procyclingstats import Team, Rider, Race
import utilidades as herramientas

# Colores Burgos BH
APP_BG = "#FFFFFF"
SURFACE = "#F7F7F7"
BORDER = "#D8D8D8"
PRIMARY_COLOR = "#D4007A"
PRIMARY_DARK = "#9C005A"
TEXT_PRIMARY = "#1A1A1A"
TEXT_SECONDARY = "#444444"
TEXT_MUTED = "#888888"
SUCCESS = "#1A7A3C"
WARNING = "#C77700"

class App:
    def __init__(self):
        # Cargar listado de carreras
        self.df_carreras = herramientas.cargar_lista_carreras()
        self.df_carreras = self.df_carreras if isinstance(self.df_carreras, pl.DataFrame) and len(self.df_carreras) > 0 else pl.DataFrame(schema={"carrera": pl.Utf8, "url": pl.Utf8})
        
        if "carrera" in self.df_carreras.columns:
            specialities = self.df_carreras.filter(pl.col("carrera").is_not_null()).select("carrera").to_series().to_list()
        elif "url" in self.df_carreras.columns:
            specialities = self.df_carreras.filter(pl.col("url").is_not_null()).select("url").to_series().to_list()
        else:
            specialities = ["(sin carreras)"]
        
        self.specialities = specialities
        self.carpeta_destino = None
        
        self.build_ui()

    def build_ui(self):
        # CSS Personalizado para adaptar estilos globales y Quasar
        ui.add_head_html('''
            <style>
            body {
                background-color: #FFFFFF;
                font-family: 'Inter', sans-serif;
                margin: 0;
                padding: 0;
                overflow-x: hidden;
            }
            .q-table__container {
                box-shadow: none !important;
                border: none !important;
            }
            .q-table th {
                font-weight: bold !important;
            }
            </style>
        ''')
        
        # Layout Principal
        with ui.column().classes('w-full').style('gap: 0; padding: 0; min-height: 100vh;'):
            # === HEADER CON ESTILO BURGOS BH ===
            with ui.row().classes('w-full items-center justify-between').style('background-color: #FFFFFF; border-bottom: 3px solid #D4007A; padding: 15px 20px; gap: 15px;'):
                with ui.row().classes('items-center').style('gap: 15px;'):
                    if os.path.exists("LOGO.png"):
                        ui.image("LOGO.png").style('width: 56px; height: 56px; object-fit: contain; background-color: #E5E5E5; padding: 8px; border-radius: 8px;')
                    with ui.column().style('gap: 4px;'):
                        ui.label("BURGOS BH").style('font-size: 26px; font-weight: bold; color: #D4007A; line-height: 1;')
                        with ui.row().style('background-color: #E5E5E5; padding: 4px 8px; border-radius: 4px;'):
                            ui.label("Racing Team").style('font-size: 12px; color: #444444; font-weight: 500;')
            
            # === SECCIÓN DE BÚSQUEDA ===
            with ui.card().classes('w-full').style('padding: 20px; margin: 15px 20px; background-color: #F7F7F7; border: 1px solid #D8D8D8; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.04); width: calc(100% - 40px);'):
                ui.label("📍 Buscar Resultados de Carrera").style('font-size: 16px; font-weight: bold; color: #1A1A1A;')
                with ui.row().classes('w-full items-center').style('gap: 12px;'):
                    self.race_dropdown = ui.select(options=self.specialities, value=self.specialities[0] if self.specialities else '').style('width: 500px; max-width: 100%;')
                    self.load_button = ui.button('🏁  BUSCAR RESULTADOS', on_click=self.on_cargar).style('width: 250px; background-color: #D4007A; color: #FFFFFF; font-weight: bold; border-radius: 8px; height: 56px;')
            
            # === STATS BAR ===
            def crear_tarjeta_stat(titulo, valor, color_valor):
                card = ui.card().style('padding: 15px; width: 180px; background-color: #F7F7F7; border: 1px solid #D8D8D8; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);')
                with card:
                    ui.label(titulo).style('font-size: 11px; color: #888888; font-weight: bold;')
                    lbl = ui.label(valor).style(f'font-size: 24px; font-weight: bold; color: {color_valor};')
                return lbl

            with ui.row().classes('w-full').style('padding: 5px 20px 15px 20px; background-color: #FFFFFF; gap: 15px;'):
                self.stat_count = crear_tarjeta_stat("Resultados", "0", PRIMARY_COLOR)
                self.stat_status = crear_tarjeta_stat("Estado", "Listo", SUCCESS)
                crear_tarjeta_stat("Formato Descarga", "Excel", TEXT_SECONDARY)
            
            # === ÁREA DE CONTENIDO (TABLA O CARGA) ===
            with ui.row().classes('w-full').style('position: relative; padding: 0 20px 20px 20px; min-height: 350px;'):
                # Contenedor de la Tabla
                self.table_container = ui.card().classes('w-full').style('padding: 12px; border: 1px solid #D8D8D8; border-radius: 8px; background-color: #F7F7F7; box-shadow: 0 2px 5px rgba(0,0,0,0.04); min-height: 300px; width: 100%;')
                with self.table_container:
                    self.data_table = ui.table(columns=[
                        {'name': 'placeholder', 'label': 'Esperando datos...', 'field': 'placeholder', 'align': 'center'}
                    ], rows=[]).classes('w-full')
                
                # Indicador de Carga
                self.loading_indicator = ui.column().classes('absolute-center items-center justify-center').style('gap: 15px; z-index: 10; width: 100%; text-align: center;')
                with self.loading_indicator:
                    ui.spinner(size='80px', color=PRIMARY_COLOR)
                    ui.label("Cargando resultados...").style('font-size: 18px; font-weight: bold; color: #D4007A;')
                    ui.label("Por favor espera").style('font-size: 12px; color: #888888;')
                
                # Ocultar indicador de carga inicialmente
                self.loading_indicator.visible = False

    async def on_cargar(self):
        import tkinter as tk
        from tkinter import filedialog
        
        print("✅ Botón búsqueda presionado")
        
        # Selección nativa de directorio en hilo secundario para evitar bloquear la UI
        def pick_directory():
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes('-topmost', 1)
            carpeta = filedialog.askdirectory(title="Seleccionar carpeta de destino")
            root.destroy()
            return carpeta
            
        carpeta = await run.io_bound(pick_directory)
        
        if carpeta:
            print(f"✅ Carpeta seleccionada: {carpeta}")
            await self.iniciar_busqueda(carpeta)
        else:
            print("ℹ️ Selección de carpeta cancelada")

    def mostrar_carga(self, mostrar: bool):
        self.loading_indicator.visible = mostrar
        self.table_container.visible = not mostrar

    async def iniciar_busqueda(self, carpeta_destino):
        try:
            if not os.path.exists(carpeta_destino):
                os.makedirs(carpeta_destino)
            
            self.carpeta_destino = carpeta_destino
            
            # Mostrar cargando y deshabilitar botón
            self.mostrar_carga(True)
            self.load_button.disable()
            
            # Obtener selección
            seleccionado = self.race_dropdown.value
            fila = self.df_carreras.filter(pl.col("carrera").cast(pl.Utf8) == str(seleccionado))
            hiperv = None
            if len(fila) > 0:
                hiperv = fila[0, "url"]
            
            consulta = hiperv if hiperv else seleccionado
            print("Consulta para buscar resultados:", consulta)
            
            # Ejecutar scraping bloqueante en hilo secundario
            resultados, archivo_guardado = await run.io_bound(
                herramientas.buscar_resultados_carrera,
                consulta,
                self.carpeta_destino
            )
            
            self.mostrar_resultados(resultados, archivo_guardado)
            
        except Exception as ex:
            print(f"Error en búsqueda: {ex}")
            self.mostrar_resultados(None, None)
            
        finally:
            self.load_button.enable()

    def mostrar_resultados(self, resultados, archivo_guardado=None):
        self.mostrar_carga(False)
        
        if resultados is None or (isinstance(resultados, pl.DataFrame) and resultados.is_empty()):
            self.data_table.columns = [{'name': 'estado', 'label': 'Estado', 'field': 'estado', 'align': 'center'}]
            self.data_table.rows = [{'estado': '❌ No hay resultados disponibles'}]
            self.data_table.update()
            
            self.stat_count.set_text("0")
            self.stat_status.set_text("Sin datos")
            self.stat_status.style(f'font-size: 24px; font-weight: bold; color: {WARNING};')
            
            self.mostrar_dialogo("❌ Error", "No se encontraron resultados disponibles para esta carrera.")
            return

        # Mapeo de columnas con nombres en español
        mapeo_columnas = {
            "rank": "🏅 Pos",
            "rider_name": "👤 Corredor",
            "team_name": "🏢 Equipo",
            "time": "⏱️ Tiempo",
            "speciality": "🎯 Especialidad",
            "especialidad": "🎯 Especialidad",
            "edition": "📅 Edición",
            "startdate": "📍 Inicio",
            "date": "📆 Fecha",
            "distance": "📏 Distancia",
            "average_speed": "⚡ Vel. Media",
            "uci_points": "⭐ Puntos UCI",
            "age": "🎂 Edad",
            "nation": "🌍 País",
            "result": "📊 Resultado",
            "stage_name": "🗻 Etapa",
            "season": "🔢 Temporada",
        }
        
        cols = [str(c) for c in resultados.columns]
        columns = [
            {
                'name': col_name,
                'label': mapeo_columnas.get(col_name, col_name.replace("_", " ").title()),
                'field': col_name,
                'align': 'center',
                'sortable': True
            }
            for col_name in cols
        ]
        
        rows = []
        for idx, row_dict in enumerate(resultados.to_dicts()[:100]):
            row = {}
            for col_name in cols:
                valor = str(row_dict.get(col_name, ""))
                if len(valor) > 40:
                    valor = valor[:37] + "..."
                row[col_name] = valor
            rows.append(row)
            
        self.data_table.columns = columns
        self.data_table.rows = rows
        self.data_table.update()
        
        total_count = len(resultados)
        displayed_count = min(100, total_count)
        
        self.stat_count.set_text(str(displayed_count))
        self.stat_status.set_text("✅ Cargado")
        self.stat_status.style(f'font-size: 24px; font-weight: bold; color: {SUCCESS};')
        
        if archivo_guardado:
            self.mostrar_dialogo(
                "✅ Búsqueda Completada",
                f"📊 Se cargaron {total_count} resultados\n"
                f"📋 Mostrando {displayed_count} registros\n\n"
                f"📥 Archivo Excel generado:\n{archivo_guardado}"
            )
        else:
            self.mostrar_dialogo(
                "✅ Datos Cargados",
                f"Se cargaron {displayed_count} de {total_count} resultados"
            )

    def mostrar_dialogo(self, titulo: str, mensaje: str):
        with ui.dialog() as dialog, ui.card().style('padding: 20px; border-radius: 8px; min-width: 300px;'):
            ui.label(titulo).style('font-size: 18px; font-weight: bold; color: #D4007A;')
            ui.label(mensaje).style('font-size: 13px; color: #444444; white-space: pre-line;')
            ui.button('Cerrar', on_click=dialog.close).style('background-color: #D4007A; color: #FFFFFF; margin-top: 15px;')
        dialog.open()

@ui.page('/')
def main():
    App()

if __name__ in {"__main__", "__mp_main__"}:
    # Inicia la aplicación en el navegador web por defecto para mayor estabilidad
    ui.run(native=False, title="🚴 Cycling Team Viewer - Burgos BH", reload=False)