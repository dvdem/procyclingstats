import sys
import io
import time

def _configurar_utf8_stream(stream):
    """Configura un stream con UTF-8 si es seguro hacerlo."""
    if stream is None:
        return stream
    try:
        encoding = getattr(stream, "encoding", None)
        if encoding and "utf-8" in encoding.lower():
            return stream
        buffer = getattr(stream, "buffer", None)
        if buffer is None or buffer.closed:
            return stream
        return io.TextIOWrapper(buffer, encoding="utf-8", errors="replace")
    except Exception:
        return stream

# Configure UTF-8 encoding for console output on Windows
if sys.platform == "win32":
    sys.stdout = _configurar_utf8_stream(sys.stdout)
    sys.stderr = _configurar_utf8_stream(sys.stderr)

import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
import os
import polars as pl
import gc
import requests
from io import BytesIO
from openpyxl import load_workbook,Workbook,worksheet,utils
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.worksheet.table import Table, TableStyleInfo
from procyclingstats import Race, Rider, Stage
from procyclingstats import RaceClimbs
from openpyxl.drawing.image import Image

from PIL import Image as PILImage
import numpy as np
import matplotlib.pyplot as plt
import json
"""Base class for all scraping classes."""
BASE_URL: str = "https://www.procyclingstats.com/"

def _obtener_con_reintentos(crear_objeto_func, max_reintentos=3, delay_inicial=1):
    """
    Intenta crear un objeto (Rider, Stage, Race) con reintentos exponenciales.
    
    Args:
        crear_objeto_func: Función que crea el objeto (ej: lambda: Rider(url))
        max_reintentos: Número máximo de reintentos
        delay_inicial: Delay inicial en segundos
    
    Returns:
        El objeto creado o None si todos los reintentos fallan
    """
    for intento in range(max_reintentos):
        try:
            objeto = crear_objeto_func()
            # Limpiar memoria después de crear objeto
            gc.collect()
            return objeto
        except (IOError, OSError, ValueError) as e:
            if intento < max_reintentos - 1:
                delay = delay_inicial * (2 ** intento)  # Exponencial: 1, 2, 4 segundos
                print(f"⚠️ Intento {intento + 1}/{max_reintentos} falló: {str(e)[:80]}. Reintentando en {delay}s...")
                time.sleep(delay)
            else:
                print(f"❌ Error después de {max_reintentos} intentos: {str(e)[:80]}")
                return None
        except Exception as e:
            print(f"❌ Error inesperado: {str(e)}")
            return None
    return None

# carga la lista de carreras desde un fichero Excel alojado en Dropbox
def cargar_lista_carreras():
    
    # Increase the decompression bomb limit for large Excel files
    PILImage.MAX_IMAGE_PIXELS = None
    
    data = []
    url="https://www.dropbox.com/scl/fi/k9vozw3agqbbdx6si4rvx/Burgos-Burpellet-BH-26.xlsx?rlkey=j8ch74vpx7g82bx4ee3bfho3b&dl=1"
    #url=("C://Users//echav//Dropbox//DIRECCIÓN BBH26//CARRERAS 2026//Burgos-Burpellet-BH 26.xlsx")
    try:
       
        # Check if URL is a web URL or local file path
        if url.startswith(('http://', 'https://')):
            # For web URLs, use requests
            response = requests.get(url)
            response.raise_for_status()  
            # para asegurar descarga correcta
            archivo_memoria = BytesIO(response.content)
            wb=openpyxl.load_workbook(archivo_memoria)
        else:
            # For local file paths, load directly
            wb=openpyxl.load_workbook(url)
        print("Fichero cargado correctamente.")
        ws = wb.active
        
        if wb and ws:
                for row in ws.iter_rows(min_col=2, min_row=1, max_row=5, values_only=False):
                    for celda in row:
                        if celda.hyperlink:
                            data.append({"carrera": celda.value, "url": str(celda.hyperlink.target).split(".com/")[-1]})
                            #print(f"{celda.value}: {celda.hyperlink.target}")
        
        if data:
            carrera = pl.DataFrame(data)
        else:
            carrera = pl.DataFrame(schema={"carrera": pl.Utf8, "url": pl.Utf8})
        
    except FileNotFoundError:
        print(f"El fichero '{url}' no existe.")
       
    except Exception as e:
        print(f"Error al cargar el fichero: {e}")  
     
    return carrera

def find_logo_path(filename: str = "logo.png"):
    """Intenta resolver la ruta del logo.
    Prioriza env var ``PCS_LOGO_PATH`` y la ruta estándar ``web_carreras/assets/logo.png``.
    Devuelve la ruta absoluta si existe, o None si no se encuentra.
    """
    # 1) Variable de entorno
    env_path = os.getenv("PCS_LOGO_PATH")
    if env_path and os.path.exists(env_path):
        return os.path.abspath(env_path)

    # 2) Ubicaciones relativas comunes
    try:
        file_dir = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        file_dir = os.getcwd()
    cwd = os.getcwd()

    standard_rel = os.path.join("web_carreras", "assets", filename)
    candidates = [
        # Ubicación estándar dentro del proyecto
        os.path.join(file_dir, standard_rel),
        os.path.join(cwd, standard_rel),
        # Compatibilidad retro: raíz del proyecto
        os.path.join(file_dir, filename),
        os.path.join(cwd, filename),
        # Compatibilidad retro: web_carreras/ directo
        os.path.join(file_dir, "web_carreras", filename),
        os.path.join(cwd, "web_carreras", filename),
    ]
    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)
    return None

def buscar_resultados_carrera(enlace_o_valor, carpeta_destino=None):
    """
    Intenta obtener resultados de carrera usando procyclingstats.Race.
    entrada: puede ser una URL completa, un slug o None.
    carpeta_destino: carpeta donde guardar el archivo Excel (opcional, default: 'data/')
    devuelve: DataFrame con resultados o None si falla.
    """
    if not enlace_o_valor:
        print("No se proporcionó enlace o valor.")
        return None
      
    try:
        print("Intentando obtener resultados para:", f"{BASE_URL}{enlace_o_valor}")
        
        # Crear Race object con reintentos
        race = _obtener_con_reintentos(
            lambda: Race(f"{BASE_URL}{enlace_o_valor}/overview"),
            max_reintentos=3
        )
        
        if race is None:
            print("No se pudo obtener información de la carrera después de reintentos.")
            return None, None
        
        df_fin = None
        
        # Si es carrera de un día
        if race.is_one_day_race(): 
            df_fin, archivo_guardado = one_day_race_results(enlace_o_valor, carpeta_destino, race)
        else:
            # Si es carrera de múltiples etapas
            stages = race.stages() 
            
            for stage_info in stages:
                try:
                    # Obtener stage con reintentos
                    stage = _obtener_con_reintentos(
                        lambda si=stage_info: Stage(si['stage_url']),
                        max_reintentos=2
                    )
                    
                    if stage is None:
                        print(f"⚠️ No se pudo obtener información de etapa: {stage_info.get('stage_url', 'desconocida')}")
                        continue
                    
                    print("Obteniendo resultados de la etapa:", stage.relative_url())
                    # Obtener resultados de la etapa
                    df_res = pl.DataFrame(stage.parse().get('results', []))
                    
                    if df_fin is None:
                        df_fin = df_res.head(10)
                    else:
                        df_fin = pl.concat([df_fin, df_res.head(10)])
                    
                    # Limpiar memoria
                    gc.collect()
                    
                except Exception as e:
                    print(f"⚠️ Error procesando etapa: {str(e)}")
                    continue
            
            # Para carreras por etapas, no hay archivo guardado
            archivo_guardado = None
        
        # Retornar con nombres consistentes
        if df_fin is not None:
            resultado = df_fin.select(['rank', 'rider_name', 'team_name', 'uci_points'])
        else:
            resultado = None
            
        return resultado, archivo_guardado
           
    except Exception as e:
        print("Error al obtener resultados de la carrera:", e)
        return None, None 
def pintar_grafico_en_excel(hojas, df_especialidades_completo, row, column, df_especialidades_bbh=None, ancho=600, alto=600,year=2025):
    """
    Crea un gráfico radial (general vs opcional Burgos BH) y lo inserta en Excel.

    Args:
        hojas: Worksheet de openpyxl donde insertar el gráfico
        df_especialidades_completo: DataFrame de Polars con las especialidades generales
        row: Fila donde insertar la esquina superior de la imagen
        column: Columna donde insertar la esquina superior de la imagen
        df_especialidades_bbh: DataFrame de Polars para Burgos BH (opcional)
        ancho: Ancho de la imagen en píxeles (por defecto 600)
        alto: Alto de la imagen en píxeles (por defecto 600)
    """
    if df_especialidades_completo is None or df_especialidades_completo.is_empty():
        print("⚠️ No hay datos de especialidades para crear el gráfico")
        return
    
    # Columnas de especialidades (excluir rider_name, edition, position)
    cols_general = [c for c in df_especialidades_completo.columns if c not in ['rider_name', 'edition', 'position']]
    cols_bbh = [c for c in df_especialidades_bbh.columns if c not in ['rider_name', 'edition', 'position']] if df_especialidades_bbh is not None else []
    if not cols_general and not cols_bbh:
        print("⚠️ No hay columnas de especialidades para graficar")
        return
    
    # Unión de categorías ordenada alfabéticamente
    categories = sorted(cols_general + [c for c in cols_bbh if c not in cols_general])
    
    def mean_for(df, col):
        return df.select(pl.col(col)).fill_null(0).mean().item() if col in df.columns else 0.0
    
    medias_general = [mean_for(df_especialidades_completo, c) for c in categories]
    medias_bbh = [mean_for(df_especialidades_bbh, c) for c in categories] if df_especialidades_bbh is not None else None
    
    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]
    
    general_plot = medias_general + [medias_general[0]]
    bbh_plot = medias_bbh + [medias_bbh[0]] if medias_bbh is not None else None
    max_val = max(general_plot + (bbh_plot or [])) if (general_plot + (bbh_plot or [])) else 1
    
    # Crear figura
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
    
    # Graficar general
    ax.plot(angles, general_plot, 'o-', linewidth=3, label='Media general', color='#FF5733')
    ax.fill(angles, general_plot, alpha=0.25, color='#FF5733')
    
    # Graficar Burgos BH si existe
    if bbh_plot is not None:
        ax.plot(angles, bbh_plot, 'o-', linewidth=3, label='Media Burgos BH', color='#1f77b4')
        ax.fill(angles, bbh_plot, alpha=0.2, color='#1f77b4')
        
        # Puntos individuales por ciclista Burgos BH
        df_bbh_pd = df_especialidades_bbh.select(categories + ['rider_name']).to_pandas()
        for idx, row_rider in df_bbh_pd.iterrows():
            vals = [row_rider.get(c, 0.0) if row_rider.get(c) is not None else 0.0 for c in categories]
            vals_loop = vals + [vals[0]]
            ax.plot(angles, vals_loop, marker='o', linestyle='', markersize=4, alpha=0.8, label=row_rider['rider_name'])
    
    # Configurar etiquetas
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, size=10, fontweight='bold')
    ax.set_ylim(0, max_val * 1.2 if max_val > 0 else 1)
    
    # Añadir cuadrícula
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Añadir título
    titulo = 'Perfil Medio de Especialidades' if bbh_plot is None else 'Perfil Medio: General vs Burgos BH'
    plt.title(titulo, size=14, y=1.08, fontweight='bold')
    if bbh_plot is not None:
        plt.legend(loc='upper right', bbox_to_anchor=(1.35, 1.05), fontsize=8)
    
    plt.tight_layout()
    
    # Guardar el gráfico como imagen temporal
    temp_image = f'temp/temp_grafico_especialidades_{year}.png'
    plt.savefig(temp_image, dpi=100, bbox_inches='tight', facecolor='white')
    plt.close()
    
    # Insertar imagen en Excel
    img = Image(temp_image)
    img.width = ancho
    img.height = alto
    celdax = utils.get_column_letter(column)
    celda = f"{celdax}{row}"
    hojas.add_image(img, celda)
def insertar_dataframe_en_excel(hojas, df_pandas,row, start_col=1):
    """
    Inserta encabezados y datos de un DataFrame en la hoja de Excel con formato.

    Args:
        hojas: Worksheet de openpyxl
        df_pandas: DataFrame en pandas para insertar
        row: Fila inicial para insertar el DataFrame
        start_col: Columna inicial para insertar el DataFrame (por defecto 1)
    """
    # Insertar encabezados del DataFrame
    for col_idx, col_name in enumerate(df_pandas.columns, start=start_col):
        cell = hojas.cell(row=row, column=col_idx, value=col_name)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
        cell.alignment = Alignment(horizontal='center')
    
    # Insertar datos del DataFrame
    for row_idx, row in enumerate(df_pandas.values, start=row + 1):
        for col_idx, value in enumerate(row, start=start_col):
            hojas.cell(row=row_idx, column=col_idx, value=value)
    
def one_day_race_results(race_slug, carpeta_destino=None,carre=None):
    print("one_day_race_results")
   # race = Race(f"{BASE_URL}{race_slug}/overview")

    
    #race = Race(f"{race_slug}/overview") 
    
    # No construir un DataFrame con race.parse() ya que mezcla listas y escalares
    # que provocan columnas con longitudes distintas. Usar el dict directamente.
    data = carre.parse()

    print("Generando archivo Excel para la carrera:")
    
    # Usar la carpeta de destino proporcionada o la carpeta 'data/' por defecto
    if carpeta_destino:
        file = os.path.join(carpeta_destino, f"HISTORIA_{data['name'].replace(' ', '_')}.xlsx")
    else:
        file = f"data/HISTORIA_{data['name'].replace(' ', '_')}.xlsx"
    
    # DataFrame para acumular todos los top 10
    df_todos_top10 = []
    
    print("Archivo de salida:", file)
    libros=Workbook()
    hojas=libros.active
   
    enlace_o_valor = race_slug
    # Insertar logo en A1
    logo = Image('LOGO.png')
    logo.width = 250
    logo.height =100
    hojas.add_image(logo, 'A1')

    df_fin = None
    #list_editions = race.prev_editions_select() 
    c=hojas.max_row
    df_especialidades_todos_bbh = []
    # DataFrame para almacenar todas las especialidades
    df_especialidades_todos = []
    # DataFrame para especialidades de Burgos BH
    df_especialidades_todos_bbh = []

    hojas.cell(row=3, column=3, value=str(data['uci_tour'])+" "+data['name']+":"+str(data['startdate'])) # type: ignore
    hojas['C3'].font = Font(color='FF0000', bold=True,size=25)    
    print("Ediciones encontradas:", len(data['prev_editions_select'] ))
    for res in data['prev_editions_select'][0:6]:
        print("Procesando edición:", res['text'])
        c=hojas.max_row+2
        
        cell=hojas.cell(row=c, column=1, value=f"Procesando edición {res['text']}")
        cell.font = Font(bold=True,size=15)
        past_edit=Stage(f"{BASE_URL}{enlace_o_valor.strip()[0:len(enlace_o_valor)-4]}{res['text']}/result")
                
        cell = hojas.cell(row=c+2, column=1, value=f'{past_edit.won_how()}')
        cell.font = Font(color='FF0000',bold=True)
        hojas.cell(row=c+2, column=2, value=f'participacion:{past_edit.race_startlist_quality_score()}' )
        hojas.cell(row=c+2, column=3, value=f'desnivel: {past_edit.vertical_meters()}m')
        hojas.cell(row=c+2, column=4, value=f'distancia {past_edit.distance()}km' )
        hojas.cell(row=c+2, column=5, value=f'avg:{past_edit.avg_speed_winner()}km/h')

         #buscar puertos de la edición
        race_climbs = RaceClimbs(f"{BASE_URL}{enlace_o_valor.strip()[0:len(enlace_o_valor)-4]}{res['text']}/route/climbs")
        # Transformar lista de climbs() a DataFrame
        climbs_list = race_climbs.climbs()
        df_climbs_list = pl.DataFrame(climbs_list)

        # Solo procesar si hay datos y existe la columna esperada
        if not df_climbs_list.is_empty() and 'km_before_finnish' in df_climbs_list.columns:
            df_climbs_list = df_climbs_list.sort('km_before_finnish', descending=True)
            # Insertar DataFrame de puertos en Excel
            insertar_dataframe_en_excel(
                hojas,
                df_climbs_list.select([
                    pl.col('climb_name').alias('Puerto'),
                    pl.col('length').alias('Longitud'),
                    pl.col('steepness').alias('Desnivel'),
                    pl.col('top').alias('Altitud'),
                    pl.col('km_before_finnish').alias('km a meta')
                ]).to_pandas(),
                c + 4
            )
        else:
            hojas.cell(row=c+4, column=1, value="Sin datos de puertos para esta edición")
        
        df_res = pl.DataFrame(past_edit.parse()['results'])
            
        if(df_res.is_empty()):
            print("  No hay resultados para esta edición.")
            hojas.cell(row=c+3, column=1, value="  No hay resultados para esta edición.")
            continue
        
        # Obtener especialidades para cada rider
        especialidades = []
        for idx, txirrindu in enumerate(df_res.head(10).select('rider_url', 'rider_name').iter_rows()):      
            if not txirrindu or len(txirrindu) < 2:
                print(f"⚠️ Datos incompletos en fila {idx}, saltando...")
                especialidades.append("sin datos")
                continue
            rider_url, rider_name = txirrindu
            try:
                # Obtener Rider con reintentos
                rider = _obtener_con_reintentos(
                    lambda ru=str(rider_url): Rider(ru),
                    max_reintentos=2
                )
                
                if rider is None:
                    print(f"⚠️ No se pudo obtener datos del ciclista {rider_name}")
                    especialidades.append("No disponible")
                    continue
            
                points_per_speciality = rider.parse()['points_per_speciality']
                if isinstance(points_per_speciality, dict):
                    sorted_by_values = dict(sorted(points_per_speciality.items(), key=lambda item: item[1], reverse=True))
                    df_rider_specialidad = pl.DataFrame([sorted_by_values])
                else:
                    df_rider_specialidad = pl.DataFrame(points_per_speciality) 
            
                # Agregar información del rider y edición al DataFrame de especialidades
                df_rider_specialidad = df_rider_specialidad.with_columns([
                    pl.lit(rider_name).alias('rider_name'),
                    #pl.lit(res['text']).alias('edition'),
                    pl.lit(idx + 1).alias('position')
                ])
                df_especialidades_todos.append(df_rider_specialidad)
            
                cols = list(df_rider_specialidad.columns)
                row_values = df_rider_specialidad.row(0)
                # Buscar las columnas que no son las que agregamos
                cols_especialidad = [c for c in cols if c not in ['rider_name', 'edition', 'position']]
                if len(cols_especialidad) >= 2:
                    especialidad = cols_especialidad[0]+":"+str(row_values[cols.index(cols_especialidad[0])])+","+cols_especialidad[1]+":"+str(row_values[cols.index(cols_especialidad[1])])
                elif len(cols_especialidad) == 1:
                    especialidad = cols_especialidad[0]+":"+str(row_values[cols.index(cols_especialidad[0])])
                else:
                    especialidad = "sin datos"
                
            except Exception as e:
                print(f"⚠️ Error procesando rider {rider_name}: {str(e)}")
                especialidad = "Error al obtener datos"
            
            especialidades.append(especialidad)
            # Limpiar memoria entre riders
            gc.collect()
            
        
        # Agregar columna de especialidad a df_res
        if len(especialidades) > 0:
            df_res_como = df_res.head(len(especialidades)).with_columns(pl.Series('especialidad', especialidades))
        
        # Insertar resultados generales (top 10)
        row_top10 = hojas.max_row + 2
        df_pandas = df_res_como.select([pl.col('rank').alias('Posicion'), pl.col('rider_name').alias('Nombre'), pl.col('time').alias('Tiempo'),pl.col('team_name').alias('Equipo'), pl.col('especialidad').alias('Especialidad')]).to_pandas()
        insertar_dataframe_en_excel(hojas, df_pandas, row_top10)
        
        # Agregar edición a los resultados para el treeview (mantener nombres originales)
        df_top10_edicion = df_res_como.select([
            'rank',
            'rider_name',
            'team_name',
            'time',
            'especialidad'
        ]).with_columns([
            pl.lit(res['text']).alias('edition')
        ])
        df_todos_top10.append(df_top10_edicion)
        
        # Insertar puntos UCI por equipos (a la derecha del top 10)
        df_pandas_uci=df_res.group_by('team_name').agg(pl.col('uci_points').sum()).filter(pl.col('uci_points') > 0).sort('uci_points', descending=True).to_pandas()
        df_pandas_uci = df_pandas_uci.rename(columns={'team_name': 'Equipo', 'uci_points': 'Puntos UCI'})
        
        insertar_dataframe_en_excel(hojas, df_pandas_uci, row_top10, start_col=7)

        # Insertar resultados del equipo Burgos
        df_burgos = df_res.filter(pl.col('team_name').str.contains('Burgos', strict=False))
        df_pandas = df_burgos.select([pl.col('rank').alias('Posicion'), pl.col('rider_name').alias('Nombre'), pl.col('time').alias('Tiempo'), pl.col('breakaway_kms').alias('Kms en fuga'), pl.col('uci_points').alias('Puntos UCI  ')]).to_pandas()
        insertar_dataframe_en_excel(hojas, df_pandas,row_top10+16)
    
        #preparando especialidades de Burgos BH para gráfico separado
    
        # Obtener especialidades para cada rider bbh
        especialidadesbbh = []
        especialidadbh = ""
        for idx, bagos in enumerate(df_burgos.select('rider_url', 'rider_name').iter_rows()):      
            if not bagos or len(bagos) < 2:
                print(f"⚠️ Datos incompletos en fila BBH {idx}, saltando...")
                especialidadesbbh.append("sin datos")
                continue
            try:
                rider_url, rider_name = bagos
                
                # Obtener Rider con reintentos
                riderbbh = _obtener_con_reintentos(
                    lambda ru=str(rider_url): Rider(ru),
                    max_reintentos=2
                )
                
                if riderbbh is None:
                    print(f"⚠️ No se pudo obtener datos del ciclista BBH {rider_name}")
                    especialidadbh = "No disponible"
                else:
                    points_per_speciality = riderbbh.parse()['points_per_speciality']
                    if isinstance(points_per_speciality, dict):
                        sorted_by_values = dict(sorted(points_per_speciality.items(), key=lambda item: item[1], reverse=True))
                        df_rider_specialidad = pl.DataFrame([sorted_by_values])
                    else:
                        df_rider_specialidad = pl.DataFrame(points_per_speciality) 
                
                    # Agregar información del rider y edición al DataFrame de especialidades
                    df_rider_specialidad_bbh = df_rider_specialidad.with_columns([
                    pl.lit(rider_name).alias('rider_name'),
                    #pl.lit(edition['text']).alias('edition'),
                    pl.lit(idx + 1).alias('position')
                ])
                    df_especialidades_todos_bbh.append(df_rider_specialidad_bbh)
                
                    cols = list(df_rider_specialidad_bbh.columns)
                    row_values = df_rider_specialidad_bbh.row(0)
                    # Buscar las columnas que no son las que agregamos
                    cols_especialidad_bh = [c for c in cols if c not in ['rider_name', 'edition', 'position']]
                
                    if len(cols_especialidad_bh) >= 2:
                        especialidadbh = cols_especialidad_bh[0]+":"+str(row_values[cols.index(cols_especialidad_bh[0])])+","+cols_especialidad_bh[1]+":"+str(row_values[cols.index(cols_especialidad_bh[1])])
                    elif len(cols_especialidad_bh) == 1:
                        especialidadbh = cols_especialidad_bh[0]+":"+str(row_values[cols.index(cols_especialidad_bh[0])])
                    else:
                        especialidadbh = "sin datos"
            except Exception as e:
                print(f"⚠️ Error procesando rider BBH {rider_name}: {str(e)}")
                especialidadbh = "Error al obtener datos"
            
            especialidadesbbh.append(especialidadbh)
            # Limpiar memoria entre riders
            gc.collect()
            
        
        # Agregar columna de especialidad a df_res
        if len(especialidadesbbh) > 0:
            df_res_como_bbh = df_res.head(len(especialidadesbbh)).with_columns(pl.Series('especialidad', especialidadesbbh))

        # Concatenar todos los DataFrames de especialidades
        if df_especialidades_todos:
            df_especialidades_completo = pl.concat(df_especialidades_todos, how='diagonal')
            print("\n📊 DataFrame de especialidades creado con", len(df_especialidades_completo), "riders")
    
        else:
            df_especialidades_completo = None
            print("\n⚠️ No se encontraron especialidades")

        # Concatenar especialidades de Burgos BH
        if df_especialidades_todos_bbh:
            df_especialidades_bbh_completo = pl.concat(df_especialidades_todos_bbh, how='diagonal')
            print("\n📊 DataFrame de especialidades Burgos BH creado con", len(df_especialidades_bbh_completo), "riders")
        
        else:
            df_especialidades_bbh_completo = None
            print("\n⚠️ No se encontraron especialidades de Burgos BH")

        # Insertar gráfico combinado en Excel
        # Asegurar texto de edición para el parámetro year
        edition_text = res['text'] if isinstance(res, dict) and 'text' in res else str(res)
        pintar_grafico_en_excel(hojas, df_especialidades_completo, row_top10, 10, df_especialidades_bbh_completo, ancho=500, alto=400, year=edition_text)
        
        # Vaciar las listas de especialidades después de escribir el gráfico en Excel
        df_especialidades_todos.clear()
        df_especialidades_todos_bbh.clear()
        print("fin for edición")
    
        gc.collect() 
    # Ajustar ancho de columnas al contenido
    # Ajustar ancho de columnas al contenido
    for column_cells in hojas.columns:
        max_length = 0
        column_letter = utils.get_column_letter(column_cells[0].column)
        for cell in column_cells:
            if cell.value is not None:
               max_length = max(max_length, len(str(cell.value)))
        hojas.column_dimensions[column_letter].width = min(max_length + 2, 45)
    
    # Guardar archivo Excel
    libros.save(file)
    print(f"✅ Archivo guardado: {file}")
    
    # Consolidar todos los top 10 en un solo DataFrame
    if df_todos_top10:
        df_resultado_final = pl.concat(df_todos_top10, how='diagonal')
        # Asegurar que tiene las columnas esperadas
        return df_resultado_final, file
    else:
        return None, file
   


if __name__ == "__main__": 
    #cargar_lista_carreras(
    buscar_resultados_carrera("race/trofeo-palma/2026")