import flet as ft
import polars as pl
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_PCS_ROOT = os.path.join(PROJECT_DIR, "procyclingstats")
if os.path.isdir(os.path.join(LOCAL_PCS_ROOT, "procyclingstats")) and LOCAL_PCS_ROOT not in sys.path:
    sys.path.insert(0, LOCAL_PCS_ROOT)

from procyclingstats import Team, Rider, Race
import utilidades as herramientas
import threading

# Paleta Burgos BH - Colores del equipo profesional
# Rojo/Burdeos profesional + Negro elegante + Blanco limpio
# Paleta Burgos BH - Tema claro estilo logo (blanco + magenta)
APP_BG = "#FFFFFF"        # Blanco puro (fondo principal)
SURFACE = "#F7F7F7"       # Blanco roto (superficies)
SURFACE_ALT = "#EFEFEF"   # Gris muy claro (elementos alternos)
SURFACE_HOVER = "#E5E5E5" # Gris claro (hover)

# Colores de Burgos BH (magenta/fucsia del logo)
PRIMARY_COLOR = "#D4007A"  # Magenta intenso del logo
PRIMARY_DARK = "#9C005A"   # Magenta oscuro para énfasis
PRIMARY_LIGHT = "#FF4DA6"  # Rosa claro para acentos

# Textos
TEXT_PRIMARY = "#1A1A1A"   # Negro suave
TEXT_SECONDARY = "#444444" # Gris oscuro
TEXT_MUTED = "#888888"     # Gris medio
TEXT_ACCENT = "#D4007A"    # Magenta para énfasis textual

# Elementos UI
SUCCESS = "#1A7A3C"   # Verde oscuro (visible en blanco)
WARNING = "#C77700"   # Ámbar oscuro
DANGER = "#C0392B"    # Rojo
BORDER = "#D8D8D8"    # Borde gris claro
BORDER_ACCENT = "#D4007A"  # Borde magenta para énfasis

# Header
HEADER_BG = "#FFFFFF"      # Fondo header blanco
HEADER_ACCENT = "#D4007A"  # Acento header magenta

class App:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "🚴 Cycling Team Viewer - Burgos BH"
        self.page.window.width = 1400
        self.page.window.height = 850
        self.page.window.min_width = 1000
        self.page.window.min_height = 700
        self.page.theme_mode = ft.ThemeMode.LIGHT
        
        # Cargar ícono si existe
        logo_path = "LOGO.png"
        if os.path.exists(logo_path):
            try:
                self.page.window.icon = logo_path
            except Exception as e:
                print(f"No se pudo cargar el icono: {e}")
        
        # Obtener listado de carreras
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
        self.is_loading = False
        
        # Construir UI
        self.build_ui()
    
    def build_ui(self):
        """Construir la interfaz de usuario con estilo Burgos BH moderno"""
        self.page.bgcolor = APP_BG
        
        # === HEADER CON ESTILO BURGOS BH ===
        header_left = []
        
        logo_path = "LOGO.png"
        if os.path.exists(logo_path):
            try:
                header_left.append(
                    ft.Container(
                        content=ft.Image(
                            src=logo_path,
                            width=56,
                            height=56,
                            fit=ft.ImageFit.CONTAIN
                        ),
                        padding=8,
                        bgcolor=SURFACE_HOVER,
                        border_radius=8
                    )
                )
            except Exception as e:
                print(f"No se pudo cargar el logo: {e}")
        
        header_left.append(
            ft.Column(
                controls=[
                    ft.Text(
                        "BURGOS BH",
                        size=26,
                        weight="bold",
                        color=PRIMARY_COLOR
                    ),
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Text(
                                    "Racing Team",
                                    size=12,
                                    color=TEXT_SECONDARY
                                ),
                                padding=ft.padding.symmetric(8, 4),
                                bgcolor=SURFACE_HOVER,
                                border_radius=4
                            )
                        ]
                    )
                ],
                spacing=4
            )
        )
        
        header_top = ft.Container(
            content=ft.Row(
                controls=header_left + [ft.Container(expand=True)],
                spacing=15,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            padding=ft.padding.symmetric(20, 15),
            bgcolor=HEADER_BG,
            border=ft.border.only(
                bottom=ft.border.BorderSide(3, PRIMARY_COLOR)
            )
        )
        
        # === SECCIÓN DE BÚSQUEDA MODERNA ===
        self.race_dropdown = ft.Dropdown(
            label="Selecciona una carrera",
            options=[ft.dropdown.Option(s) for s in self.specialities],
            value=self.specialities[0] if self.specialities else "(sin carreras)",
            width=500,
            color=TEXT_PRIMARY,
            label_style=ft.TextStyle(color=TEXT_MUTED, size=13),
            text_style=ft.TextStyle(color=TEXT_PRIMARY, size=14),
            filled=True,
            bgcolor=SURFACE,
            border_color=BORDER,
            focused_border_color=PRIMARY_COLOR,
            border_radius=6
        )
        
        self.load_button = ft.ElevatedButton(
            text="🏁  BUSCAR RESULTADOS",
            on_click=self.on_cargar,
            bgcolor=PRIMARY_COLOR,
            color=TEXT_PRIMARY,
            width=250,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=6),
                text_style=ft.TextStyle(size=14, weight="bold")
            )
        )
        
        search_section = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "📍 Buscar Resultados de Carrera",
                        size=16,
                        weight="bold",
                        color=TEXT_PRIMARY
                    ),
                    ft.Row(
                        controls=[
                            self.race_dropdown,
                            self.load_button,
                            ft.Container(expand=True)
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    )
                ],
                spacing=12
            ),
            padding=ft.padding.symmetric(20, 15),
            bgcolor=SURFACE,
            border=ft.border.only(bottom=ft.border.BorderSide(1, BORDER))
        )
        
        # === STATS BAR ===
        self.stat_count = ft.Text("0", size=24, weight="bold", color=PRIMARY_COLOR)
        self.stat_status = ft.Text("Listo", size=12, color=SUCCESS)
        
        stats_bar = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Resultados", size=11, color=TEXT_MUTED, weight="bold"),
                                self.stat_count
                            ],
                            spacing=2
                        ),
                        padding=15
                    ),
                    ft.Container(
                        width=1,
                        bgcolor=BORDER
                    ),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Estado", size=11, color=TEXT_MUTED, weight="bold"),
                                self.stat_status
                            ],
                            spacing=2
                        ),
                        padding=15
                    ),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Descarga", size=11, color=TEXT_MUTED, weight="bold"),
                                ft.Text(
                                    "Excel",
                                    size=12,
                                    color=TEXT_SECONDARY,
                                    weight="bold"
                                )
                            ],
                            spacing=2
                        ),
                        padding=15
                    ),
                    ft.Container(expand=True)
                ],
                spacing=0
            ),
            padding=0,
            bgcolor=SURFACE_ALT,
            border=ft.border.only(bottom=ft.border.BorderSide(1, BORDER))
        )
        
        # === DATA TABLE MODERNO ===
        self.data_table = ft.DataTable(
            columns=[ft.DataColumn(
                ft.Text("Esperando datos...", weight="bold", size=12),
                numeric=False
            )],
            rows=[],
            border=ft.border.all(1, BORDER),
            bgcolor=SURFACE,
            heading_row_color=SURFACE_ALT,
            heading_row_height=48,
            data_row_min_height=44,
            divider_thickness=1,
            column_spacing=20,
            expand=True
        )
        
        self.table_container = ft.Container(
            content=ft.Row(
                controls=[self.data_table],
                scroll="auto",
                expand=True
            ),
            padding=0,
            border=ft.border.all(1, BORDER),
            border_radius=0,
            bgcolor=SURFACE,
            expand=True
        )
        
        # === LOADING INDICATOR ===
        self.loading_indicator = ft.Column(
            controls=[
                ft.Stack(
                    controls=[
                        ft.Container(
                            width=80,
                            height=80,
                            border_radius=40,
                            bgcolor=SURFACE_ALT,
                            border=ft.border.all(3, PRIMARY_COLOR)
                        ),
                        ft.ProgressRing(
                            value=None,
                            color=PRIMARY_COLOR,
                            stroke_width=4
                        )
                    ],
                    alignment=ft.alignment.center
                ),
                ft.Text(
                    "Cargando resultados...",
                    size=18,
                    weight="bold",
                    color=PRIMARY_COLOR
                ),
                ft.Text(
                    "Por favor espera",
                    size=12,
                    color=TEXT_MUTED
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            visible=False,
            expand=True
        )
        
        # === LAYOUT PRINCIPAL ===
        main_content = ft.Column(
            controls=[
                header_top,
                search_section,
                stats_bar,
                ft.Stack(
                    controls=[
                        self.table_container,
                        self.loading_indicator
                    ],
                    expand=True
                )
            ],
            spacing=0,
            expand=True
        )

        # Selector nativo de carpetas del sistema
        self.directory_picker = ft.FilePicker(on_result=self.on_directory_picked)
        self.page.overlay.append(self.directory_picker)
        
        self.page.add(main_content)
    
    def on_cargar(self, e):
        """Cargar resultados cuando se presiona el botón"""
        print("✅ Botón búsqueda presionado")
        self.directory_picker.get_directory_path(dialog_title="Seleccionar carpeta de destino")

    def on_directory_picked(self, e):
        """Recibir carpeta seleccionada desde FilePicker"""
        if e.path:
            print(f"✅ Carpeta seleccionada: {e.path}")
            self.iniciar_busqueda(e.path)
        else:
            print("ℹ️ Selección de carpeta cancelada")
    
    def mostrar_selector_directorio(self):
        """Mostrar selector simple de directorio"""
        print("📂 Abriendo selector de directorio")
        
        downloads = os.path.expanduser("~/Downloads")
        documents = os.path.expanduser("~/Documents")
        desktop = os.path.expanduser("~/Desktop")
        
        # Variable para mantener referencia al diálogo
        dlg = ft.AlertDialog(
            title=ft.Text("📂 Seleccionar Carpeta", weight="bold", color=PRIMARY_COLOR),
            content=ft.Column([
                ft.Text("¿Dónde guardar el archivo Excel?", size=12, color=TEXT_SECONDARY),
            ]),
            actions=[
                ft.TextButton(
                    "📥 Descargas",
                    on_click=lambda e: self._cerrar_y_buscar(dlg, downloads)
                ),
                ft.TextButton(
                    "📄 Documentos",
                    on_click=lambda e: self._cerrar_y_buscar(dlg, documents)
                ),
                ft.TextButton(
                    "🖥️ Escritorio",
                    on_click=lambda e: self._cerrar_y_buscar(dlg, desktop)
                ),
                ft.TextButton(
                    "Cancelar",
                    on_click=lambda e: self._cerrar_dialogo(dlg)
                ),
            ]
        )
        
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()
        print("✅ Diálogo abierto")
    
    def _cerrar_y_buscar(self, dlg, carpeta):
        """Cerrar diálogo e iniciar búsqueda con la carpeta seleccionada"""
        print(f"✅ Carpeta seleccionada: {carpeta}")
        dlg.open = False
        self.page.update()
        self.iniciar_busqueda(carpeta)
    
    def iniciar_busqueda(self, carpeta_destino):
        """Iniciar búsqueda con la carpeta seleccionada"""
        try:
            # Crear carpeta si no existe
            if not os.path.exists(carpeta_destino):
                os.makedirs(carpeta_destino)
            
            self.carpeta_destino = carpeta_destino
            print(f"Carpeta de destino seleccionada: {carpeta_destino}")
            
            # Mostrar indicador de carga
            self.mostrar_carga(True)
            
            # Desabilitar botón
            self.load_button.disabled = True
            self.page.update()
            
            # Buscar en thread separado
            def buscar_y_mostrar():
                try:
                    seleccionado = self.race_dropdown.value
                    fila = self.df_carreras.filter(pl.col("carrera").cast(pl.Utf8) == str(seleccionado))
                    hiperv = None
                    
                    if len(fila) > 0:
                        hiperv = fila[0, "url"]
                    
                    consulta = hiperv if hiperv else seleccionado
                    print("Consulta para buscar resultados:", consulta)
                    
                    resultados, archivo_guardado = herramientas.buscar_resultados_carrera(consulta, self.carpeta_destino)
                    
                    # Actualizar UI directamente (page.update() es thread-safe en Flet)
                    self.mostrar_resultados(resultados, archivo_guardado)
                except Exception as ex:
                    print(f"Error en búsqueda: {ex}")
                    self.mostrar_resultados(None, None)
            
            thread = threading.Thread(target=buscar_y_mostrar, daemon=True)
            thread.start()
        
        except Exception as ex:
            print(f"Error: {ex}")
            self.mostrar_dialogo("❌ Error", f"Ocurrió un error:\n{str(ex)}")
    
    def mostrar_carga(self, mostrar: bool):
        """Mostrar/ocultar indicador de carga"""
        self.loading_indicator.visible = mostrar
        self.is_loading = mostrar
        self.page.update()
    
    def mostrar_resultados(self, resultados, archivo_guardado=None):
        """Mostrar resultados en la tabla con estilo Burgos BH"""
        self.mostrar_carga(False)
        self.load_button.disabled = False
        
        if resultados is None or (isinstance(resultados, pl.DataFrame) and resultados.is_empty()):
            # Mostrar mensaje de sin resultados
            empty_table = ft.DataTable(
                columns=[ft.DataColumn(ft.Text("Estado", weight="bold", color=PRIMARY_COLOR))],
                rows=[ft.DataRow(cells=[ft.DataCell(
                    ft.Text("❌ No hay resultados disponibles", 
                           color=TEXT_MUTED, size=12, weight="bold")
                )])],
                border=ft.border.all(1, BORDER),
                bgcolor=SURFACE,
                heading_row_color=SURFACE_ALT
            )
            self.table_container.content.controls[0] = empty_table
            self.stat_count.value = "0"
            self.stat_count.color = PRIMARY_COLOR
            self.stat_status.value = "Sin datos"
            self.stat_status.color = WARNING
            self.page.update()
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
        
        # Preparar columnas - todas las disponibles
        cols = [str(c) for c in resultados.columns]
        n_cols = len(cols)

        columns = [
            ft.DataColumn(
                ft.Text(
                    mapeo_columnas.get(c, c.replace("_", " ").title()),
                    weight="bold",
                    size=11,
                    color=PRIMARY_COLOR,
                    text_align=ft.TextAlign.CENTER
                ),
                numeric=False
            )
            for c in cols
        ]
        
        # Preparar filas centradas - limitar a 100 filas
        rows = []
        for idx, row_dict in enumerate(resultados.to_dicts()[:100]):
            cells = []
            for c in cols:
                valor = str(row_dict.get(c, ""))
                if len(valor) > 40:
                    valor = valor[:37] + "..."
                
                color = TEXT_PRIMARY if idx % 2 == 0 else TEXT_SECONDARY
                
                cells.append(
                    ft.DataCell(
                        ft.Text(
                            valor,
                            size=11,
                            color=color,
                            text_align=ft.TextAlign.CENTER
                        )
                    )
                )
            
            rows.append(ft.DataRow(cells=cells))
        
        # Recrear DataTable expandida al ancho de ventana
        self.data_table = ft.DataTable(
            columns=columns,
            rows=rows,
            border=ft.border.all(1, BORDER),
            bgcolor=SURFACE,
            heading_row_color=SURFACE_ALT,
            heading_row_height=45,
            data_row_min_height=40,
            divider_thickness=1,
            column_spacing=20,
            expand=True
        )
        
        # Actualizar stats
        total_count = len(resultados)
        displayed_count = min(100, total_count)
        
        # Reemplazar tabla
        self.table_container.content.controls[0] = self.data_table
        
        # Actualizar estadísticas en pantalla
        self.stat_count.value = str(displayed_count)
        self.stat_count.color = PRIMARY_COLOR
        self.stat_status.value = "✅ Cargado"
        self.stat_status.color = SUCCESS
        
        self.page.update()
        
        # Mostrar diálogo de éxito
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
        """Mostrar diálogo con estilo Burgos BH"""
        dlg = ft.AlertDialog(
            title=ft.Text(
                titulo,
                size=18,
                weight="bold",
                color=PRIMARY_COLOR
            ),
            content=ft.Text(
                mensaje,
                size=13,
                color=TEXT_SECONDARY,
                selectable=True
            ),
            actions=[
                ft.TextButton(
                    "Cerrar",
                    on_click=lambda e: self.cerrar_dialogo(dlg),
                    style=ft.ButtonStyle(
                        color=PRIMARY_COLOR
                    )
                )
            ],
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=8)
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()
    
    def cerrar_dialogo(self, dlg: ft.AlertDialog):
        """Cerrar diálogo"""
        dlg.open = False
        self.page.update()


def main(page: ft.Page):
    app = App(page)


if __name__ == "__main__":
    ft.app(target=main)