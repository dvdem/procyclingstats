import customtkinter as ctk
import polars as pl
from procyclingstats import Team, Rider, Race
from tkinter import ttk, filedialog, messagebox, PhotoImage
import utilidades as herramientas
import os
from PIL import Image
import threading

# Configurar tema y colores de customtkinter - estilo moderno y sobrio
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# Paleta neutra con acento suave
APP_BG = "#F2F2F2"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F7F7F7"
TEXT_PRIMARY = "#1F2328"
TEXT_MUTED = "#6A737D"
ACCENT = "#3A6EA5"
ACCENT_HOVER = "#2F5C8F"
BORDER = "#D0D7DE"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Cycling Team Viewer - Burgos BH")
        self.geometry("1000x700")
        self.minsize(800, 600)
        
        # Establecer icono de la ventana
        logo_path = "LOGO.png"
        if os.path.exists(logo_path):
            try:
                # Usar PhotoImage directamente para iconphoto
                self.iconphoto(True, PhotoImage(file=logo_path))
            except Exception as e:
                print(f"No se pudo cargar el icono: {e}")
        
        # Obtener listado de carreras desde utilidades.cargar_excell_carreras()
        self.df_carreras = herramientas.cargar_lista_carreras()
        
        self.df_carreras = self.df_carreras if isinstance(self.df_carreras, pl.DataFrame) and len(self.df_carreras) > 0 else pl.DataFrame(schema={"carrera": pl.Utf8, "url": pl.Utf8})
        #self.df_carreras = self.df_carreras.sort("carrera")
        # Si devuelve un DataFrame directamente
        if "carrera" in self.df_carreras.columns:
            specialities = self.df_carreras.filter(pl.col("carrera").is_not_null()).select("carrera").to_series().to_list()
        elif "url" in self.df_carreras.columns:
            specialities = self.df_carreras.filter(pl.col("url").is_not_null()).select("url").to_series().to_list()

        # fallback si no hay nada
        if not specialities: # type: ignore
            specialities = ["(sin carreras)"]
        self.specialities = specialities

        # Frame principal
        self.main_frame = ctk.CTkFrame(self, fg_color=APP_BG)
        self.main_frame.pack(pady=0, padx=0, fill="both", expand=True)

        # Frame de encabezado
        self.header_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=SURFACE,
            height=80,
            border_width=1,
            border_color=BORDER,
        )
        self.header_frame.pack(pady=0, padx=0, fill="x")
        self.header_frame.pack_propagate(False)
        
        # Logo y título en el encabezado
        if os.path.exists(logo_path):
            try:
                pil_logo = Image.open(logo_path)
                pil_logo.thumbnail((60, 60), Image.Resampling.LANCZOS)
                logo_ctk = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(60, 60))
                logo_label = ctk.CTkLabel(self.header_frame, image=logo_ctk, text="")
                logo_label.pack(side="left", padx=15, pady=10)
            except Exception as e:
                print(f"No se pudo cargar logo en encabezado: {e}")
        
        title_label = ctk.CTkLabel(
            self.header_frame,
            text="Cycling Team Viewer - Burgos BH",
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT_PRIMARY,
        )
        title_label.pack(side="left", padx=10, pady=10)

        # Frame de controles mejorado
        self.controls_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=BORDER,
        )
        self.controls_frame.pack(pady=15, padx=15, fill="x")

        self.specialty_label = ctk.CTkLabel(
            self.controls_frame,
            text="Seleccionar carrera:",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_PRIMARY,
        )
        self.specialty_label.pack(side="left", padx=10, pady=10)

        self.specialty_var = ctk.StringVar(value=self.specialities[0])
        self.specialty_menu = ctk.CTkOptionMenu(
            self.controls_frame,
            variable=self.specialty_var,
            values=self.specialities,
            fg_color=SURFACE_ALT,
            button_color=ACCENT,
            dropdown_fg_color=SURFACE,
            dropdown_text_color=TEXT_PRIMARY,
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 11),
        )
        self.specialty_menu.pack(side="left", padx=5, pady=10)

        # Boton principal
        self.load_button = ctk.CTkButton(
            self.controls_frame,
            text="📥 Cargar Resultados",
            command=self.on_cargar,
            font=("Segoe UI", 12, "bold"),
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color="white",
            corner_radius=10,
        )
        self.load_button.pack(side="left", padx=15, pady=10)

        # Frame de contenido con treeview
        self.tree_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=BORDER,
        )
        self.tree_frame.pack(pady=10, padx=15, fill="both", expand=True)
        
        # Estilo para el Treeview
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            'Treeview',
            background=SURFACE,
            foreground=TEXT_PRIMARY,
            fieldbackground=SURFACE,
            font=("Segoe UI", 10),
            rowheight=26,
        )
        style.configure(
            'Treeview.Heading',
            background=SURFACE_ALT,
            foreground=TEXT_PRIMARY,
            font=("Segoe UI", 11, "bold"),
        )
        style.map(
            'Treeview',
            background=[('selected', ACCENT)],
            foreground=[('selected', 'white')],
        )
        
        self.tree = ttk.Treeview(self.tree_frame)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

# Widget de carga con animación
        self.loading_label = ctk.CTkLabel(self.main_frame, text="")
        self.loading_animation_frame = None
        self.animation_counter = 0
        self.is_animating = False

    def animate_loading(self):
        """Anima el mensaje de cargando con puntos suspensivos"""
        if not self.is_animating:
            return
        
        dots = [".", "..", "..."]
        current_dot = self.animation_counter % 3
        self.animation_counter += 1
        
        message = f"🚴 Cargando resultados{dots[current_dot]}"
        self.loading_label.configure(text=message)
        
        # Animar cada 500ms
        self.after(500, self.animate_loading)

    def show_loading_image(self):
        """Muestra el mensaje de cargando animado con bici sobre el treeview"""
        # Crear frame de carga con contenedor
        if self.loading_animation_frame is None:
            self.loading_animation_frame = ctk.CTkFrame(
                self.main_frame,
                fg_color=SURFACE,
                corner_radius=10,
                border_width=1,
                border_color=BORDER,
            )
        
        # Iniciar animación
        self.is_animating = True
        self.animation_counter = 0
        
        # Mostrar label con bici
        self.loading_label.configure(
            text="🚴 Cargando resultados.",
            font=("Segoe UI", 20, "bold"),
            text_color=ACCENT
        )
        
        self.tree_frame.pack_forget()
        self.loading_label.pack(pady=50, padx=20, fill="both", expand=True)
        self.update()
        
        # Iniciar animación
        self.animate_loading()
    
    def hide_loading_image(self):
        """Oculta el mensaje de cargando animado y muestra el treeview"""
        # Detener animación
        self.is_animating = False
        
        self.loading_label.pack_forget()
        self.tree_frame.pack(pady=10, padx=10, fill="both", expand=True)
        self.update()

    def on_cargar(self):
        """
        Obtiene el valor seleccionado, busca su hipervínculo en self.df_carreras,
        pide a utilidades.buscar_resultados_carrera() los resultados y los muestra en el Treeview.
        """
        # Preguntar ubicación de descarga del archivo Excel
        carpeta_destino = filedialog.askdirectory(
            title="Seleccionar carpeta para guardar el archivo Excel",
            initialdir=os.path.expanduser("~")
        )
        
        # Si el usuario cancela, no continuar
        if not carpeta_destino:
            messagebox.showinfo("Cancelado", "No se seleccionó ninguna carpeta. Operación cancelada.")
            return
        
        # Guardar la carpeta seleccionada para usarla en la generación del Excel
        self.carpeta_destino = carpeta_destino
        print(f"Carpeta de destino seleccionada: {carpeta_destino}")
        
        # Mostrar imagen de carga
        self.show_loading_image()
        
        # Deshabilitar botón mientras se cargan datos
        self.load_button.configure(state="disabled")
        
        # Ejecutar la búsqueda en un thread separado para no bloquear la UI
        def buscar_y_mostrar():
            try:
                seleccionado = self.specialty_var.get()
                
                # buscar primera fila cuyo 'valor' coincida
                df = self.df_carreras # type: ignore
                
                fila = df.filter(pl.col("carrera").cast(pl.Utf8) == str(seleccionado))
                hiperv = None
                print("Fila encontrada:", fila)
                if len(fila) > 0:
                    hiperv = fila[0, "url"]
                    print(fila[0, "url"])
                # si no hay hipervínculo, pasar el texto seleccionado (puede ser slug)
                consulta = hiperv if hiperv else seleccionado   
                print("Consulta para buscar resultados:", consulta)
                resultados, archivo_guardado = herramientas.buscar_resultados_carrera(consulta, self.carpeta_destino)
                
                # Actualizar UI en el thread principal
                self.after(0, lambda: self.mostrar_resultados(resultados, archivo_guardado))
            except Exception as e:
                print(f"Error en búsqueda: {e}")
                self.after(0, lambda: self.mostrar_resultados(None, None))
        
        # Iniciar thread
        thread = threading.Thread(target=buscar_y_mostrar, daemon=True)
        thread.start()
    
    def mostrar_resultados(self, resultados, archivo_guardado=None):
        """Muestra los resultados en el treeview y oculta la imagen de carga"""
        # Ocultar imagen de carga
        self.hide_loading_image()
        
        # Rehabilitar botón
        self.load_button.configure(state="normal")
        
        if resultados is not None:
            df_results = resultados.to_dicts()
        else:
            df_results = None
       
        # limpiar treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
         
        if resultados is None or (isinstance(resultados, pl.DataFrame) and resultados.is_empty()):
            # mostrar una fila simple con mensaje
            self.tree["columns"] = ("mensaje",)
            self.tree.heading("mensaje", text="Mensaje")
            self.tree.column("mensaje", width=600)
            self.tree.insert("", "end", values=("No se han obtenido resultados.",))
            return

        # Renombrar columnas para mostrar en español
        mapeo_columnas = {
            'rank': 'Posición',
            'rider_name': 'Nombre',
            'team_name': 'Equipo',
            'time': 'Tiempo',
            'especialidad': 'Especialidad',
            'edition': 'Edición',
            'uci_points': 'Puntos UCI'
        }
        
        # poblar columnas desde DataFrame
        cols = list(resultados.columns)
        cols_mostrar = [mapeo_columnas.get(c, c) for c in cols]
       
        self.tree["columns"] = cols_mostrar
        # quitar el column #0
        self.tree["show"] = "headings"
        for c_original, c_mostrar in zip(cols, cols_mostrar):
            self.tree.heading(c_mostrar, text=c_mostrar)
            self.tree.column(c_mostrar, width=120)
        # insertar filas
        
        for row_dict in resultados.to_dicts():
            values = [row_dict.get(c, "") for c in cols]
            self.tree.insert("", "end", values=values)
        
        # Mostrar mensaje de éxito con la ubicación del archivo
        if archivo_guardado:
            messagebox.showinfo(
                "Proceso completado",
                f"Archivo Excel generado exitosamente en:\n{archivo_guardado}"
            )

    def on_closing(self):
        """Cerrar la aplicación"""
        self.destroy()

        

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()