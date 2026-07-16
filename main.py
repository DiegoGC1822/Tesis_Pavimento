import json
from utils import progresiva_a_metros, parametrizar_poliline, interpolar_coordenada, validar_año_panorama, calcular_bearing
from services import obtener_poliline_ruta, consultar_street_view_metadata
from dotenv import load_dotenv
import os

def procesar_proyecto_vial(json_data, google_api_key=None):
    proyecto_id = json_data["proyecto_id"]
    
    # Extraemos el año de recolección de imagen a nivel global
    # Si no existe, usamos el año_estudio como respaldo.
    año_recoleccion = json_data.get("año_recolección_imagen", json_data.get("año_estudio"))
    
    # Extraemos la longitud oficial dictada por la tesis
    longitud_total_tesis = json_data.get("longitud_calzadas", 1000.0)
    
    print(f"=== Procesando Proyecto: {proyecto_id} (Año Objetivo: {año_recoleccion}) ===")
    
    resultado_descargas = []
    
    for calzada_nombre, calzada_info in json_data["calzadas"].items():

        if calzada_info is None:
            print(f"\n[AVISO] La calzada '{calzada_nombre}' es nula, saltando...")
            continue

        print(f"\n[Calzada]: {calzada_nombre}")
        
        coord_inicio = calzada_info["coordenadas_inicio_calzada"]
        coord_fin = calzada_info["coordenadas_fin_calzada"]
        
        # Calculamos el "Offset" inicial de la calzada (Ej. 2km = 2000m)
        offset_calzada_str = calzada_info.get("progresiva_inicio_calzada", "0+000")
        offset_calzada = progresiva_a_metros(offset_calzada_str)
        
        # 1. Obtener geometría real de la calle
        trazo_avenida = obtener_poliline_ruta(coord_inicio, coord_fin, google_api_key)
        dist_acumuladas, longitud_total_maps = parametrizar_poliline(trazo_avenida)
        
        # 2. Calcular Factor de Escala Residual con la longitud oficial
        factor_escala = longitud_total_maps / longitud_total_tesis if longitud_total_tesis > 0 else 1.0
        
        print(f" -> Longitud Maps: {longitud_total_maps:.2f}m | Longitud Tesis (Oficial): {longitud_total_tesis:.2f}m")
        print(f" -> Factor de Escala Residual de Ajuste: {factor_escala:.4f}")
        print(f" -> Offset de Progresiva descontado: {offset_calzada} metros")
        
        # Set para evitar repetir descargas del mismo pano_id en esta calzada
        panoramas_descargados = set()
        
        # 3. Procesar cada tramo (UM)
        for tramo in calzada_info["tramos"]:
            tramo_id = tramo["tramo_id"]
            
            # Restamos el offset de la calzada para "empezar de cero"
            m_inicio = progresiva_a_metros(tramo["progresiva_inicio"]) - offset_calzada
            m_fin = progresiva_a_metros(tramo["progresiva_fin"]) - offset_calzada
            
            print(f"   Procesando Tramo {tramo_id} (Distancia normalizada: {m_inicio}m a {m_fin}m)")
            
            # 4. Aplicar Estrategia de Sobremuestreo
            num_puntos = 6 
            
            # Pre-calculamos las coordenadas para poder comparar el actual con el siguiente
            puntos_calculados = []
            for j in range(num_puntos):
                alpha = j / (num_puntos - 1)
                dist_tesis = m_inicio + alpha * (m_fin - m_inicio)
                dist_maps = dist_tesis * factor_escala
                lat, lon = interpolar_coordenada(dist_maps, trazo_avenida, dist_acumuladas)
                puntos_calculados.append((lat, lon))

            # Ahora iteramos sobre los puntos calculados para generar el JSON
            for j in range(num_puntos):
                lat, lon = puntos_calculados[j]
                
                # CALCULAR HEADING (Bearing)
                # Si no es el último punto, miramos al siguiente. Si es el último, copiamos el anterior.
                if j < num_puntos - 1:
                    lat_sig, lon_sig = puntos_calculados[j+1]
                    heading = calcular_bearing(lat, lon, lat_sig, lon_sig)
                else:
                    # Copiamos el heading del punto anterior para no mirar hacia atrás
                    heading = resultado_descargas[-1].get("heading", 228.0) 

                # 5. Mitigación de Snapping y Validación
                meta = consultar_street_view_metadata(lat, lon, google_api_key)
                
                if meta.get("status") == "OK":
                    pano_id = meta.get("pano_id")
                    fecha_panorama = meta.get("date")
                    es_valido, msj_validacion = validar_año_panorama(fecha_panorama, año_recoleccion)
                    
                    if not es_valido:
                        resultado_descargas.append({
                            "tramo_id": tramo_id,
                            "punto_sobremuestreo": j + 1,
                            "heading": heading,
                            "pano_id": pano_id,
                            "descargar": False,
                            "coordenada_calculada": [lat, lon],
                            "motivo": f"Descarte temporal: {msj_validacion}"
                        })
                        continue

                    if pano_id not in panoramas_descargados:
                        panoramas_descargados.add(pano_id)
                        resultado_descargas.append({
                            "proyecto_id": proyecto_id,
                            "año_recolección_imagen": año_recoleccion,
                            "calzada": calzada_nombre,
                            "tramo_id": tramo_id,
                            "pci_clase": tramo["pci_clase"],
                            "pci_numérico": tramo["pci_numérico"],
                            "punto_sobremuestreo": j + 1,
                            "coordenada_calculada": [lat, lon],
                            "heading": heading,
                            "pano_id": pano_id,
                            "fecha_real_google": fecha_panorama,
                            "descargar": True
                        })
                    else:
                        # ... (Lógica de duplicado por snapping)
                        resultado_descargas.append({
                            "tramo_id": tramo_id,
                            "punto_sobremuestreo": j + 1,
                            "heading": heading,
                            "pano_id": pano_id,
                            "descargar": False,
                            "motivo": "Duplicado por Snapping"
                        })
                else:
                    print(f"     [!] Sin cobertura Street View en: {lat}, {lon}")
                    
    return resultado_descargas

if __name__ == "__main__":
    import argparse

    load_dotenv()
    API_KEY_GOOGLE = os.getenv("API_KEY_GOOGLE")

    # Argumentos de línea de comandos 
    parser = argparse.ArgumentParser(
        description="Genera planes de descarga de Street View por avenida."
    )
    parser.add_argument(
        "-a", "--avenidas",
        nargs="*",
        default=None,
        metavar="NOMBRE_AVENIDA",
        help=(
            "Uno o más nombres de avenida a procesar. "
            "Deben coincidir exactamente con el campo 'nombre_avenida' del dataset. "
            "Si se omite, se procesará todo el dataset. "
            "Ejemplo: --avenidas Sangarara Marañon"
        )
    )
    args = parser.parse_args()
    avenidas_solicitadas = args.avenidas  # None si no se pasó el flag

    # Cargar el dataset fijo 
    archivo_json = "Dataset-UM-Avenidas.json"

    try:
        with open(archivo_json, "r", encoding="utf-8") as f:
            datos_dataset = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] No se encontró el archivo '{archivo_json}'. "
              "Asegúrate de que esté en la misma carpeta que main.py.")
        exit(1)
    except json.JSONDecodeError:
        print(f"[ERROR] El archivo '{archivo_json}' no tiene un formato JSON válido.")
        exit(1)

    # Normalizamos: el dataset puede ser un dict único o una lista de proyectos
    if isinstance(datos_dataset, dict):
        todos_los_proyectos = [datos_dataset]
    else:
        todos_los_proyectos = datos_dataset

    # Construir índice nombre_avenida → proyectos
    indice_avenidas: dict[str, list] = {}
    for proyecto in todos_los_proyectos:
        nombre = proyecto.get("nombre_avenida")
        if nombre:
            indice_avenidas.setdefault(nombre, []).append(proyecto)

    print(f"\nAvenidas disponibles en el dataset: {sorted(indice_avenidas.keys())}")

    # Si no se especificaron avenidas, procesar todas
    if not avenidas_solicitadas:
        print("[INFO] No se especificaron avenidas. Se procesará todo el dataset.")
        avenidas_solicitadas = sorted(indice_avenidas.keys())

    # Verificar existencia de cada avenida solicitada
    avenidas_no_encontradas = [a for a in avenidas_solicitadas if a not in indice_avenidas]
    if avenidas_no_encontradas:
        print(
            f"\n[ERROR] Las siguientes avenidas no existen en '{archivo_json}':\n"
            + "\n".join(f"  - {a}" for a in avenidas_no_encontradas)
        )
        print("Verifica la ortografía y que el campo 'nombre_avenida' coincida exactamente.")
        exit(1)

    # Iterar sobre cada avenida solicitada
    for nombre_avenida in avenidas_solicitadas:
        proyectos_avenida = indice_avenidas[nombre_avenida]
        resultados_avenida = []

        print(f"\n{'='*60}")
        print(f"  AVENIDA: {nombre_avenida}  ({len(proyectos_avenida)} proyecto(s))")
        print(f"{'='*60}")

        for proyecto in proyectos_avenida:
            proyecto_id = proyecto.get("proyecto_id", "Sin_ID")
            print(f"\n--- Iniciando procesamiento de: {proyecto_id} ---")
            resultados_proyecto = procesar_proyecto_vial(proyecto, API_KEY_GOOGLE)
            resultados_avenida.extend(resultados_proyecto)

        # Guardar plan de descarga por avenida
        nombre_archivo_salida = f"plan_descarga_{nombre_avenida.replace(' ', '_')}.json"
        with open(nombre_archivo_salida, "w", encoding="utf-8") as archivo:
            json.dump(resultados_avenida, archivo, indent=2, ensure_ascii=False)

        print(
            f"\n[ÉXITO] Avenida '{nombre_avenida}' procesada. "
            f"{len(resultados_avenida)} registros guardados en '{nombre_archivo_salida}'"
        )

    print(f"\n[FIN] Se procesaron {len(avenidas_solicitadas)} avenida(s) correctamente.")