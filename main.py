import json
from utils import progresiva_a_metros, parametrizar_poliline, interpolar_coordenada, validar_año_panorama
from services import obtener_poliline_ruta, consultar_street_view_metadata
from dotenv import load_dotenv
import os

def procesar_proyecto_vial(json_data, google_api_key=None):
    proyecto_id = json_data["proyecto_id"]
    
    # NUEVO: Extraemos el año de recolección de imagen a nivel global
    # Si no existe, usamos el año_estudio como respaldo.
    año_recoleccion = json_data.get("año_recolección_imagen", json_data.get("año_estudio"))
    
    # NUEVO: Extraemos la longitud oficial dictada por la tesis
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
        
        # NUEVO: Calculamos el "Offset" inicial de la calzada (Ej. 2km = 2000m)
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
            
            # NUEVO: Restamos el offset de la calzada para "empezar de cero"
            m_inicio = progresiva_a_metros(tramo["progresiva_inicio"]) - offset_calzada
            m_fin = progresiva_a_metros(tramo["progresiva_fin"]) - offset_calzada
            
            print(f"   Procesando Tramo {tramo_id} (Distancia normalizada: {m_inicio}m a {m_fin}m)")
            
            # 4. Aplicar Estrategia de Sobremuestreo (6 puntos por  para dividirlo en 5 areas)
            num_puntos = 2
            for j in range(num_puntos):
                # Interpolación fraccional de la distancia dentro de la UM
                alpha = j / (num_puntos - 1)
                dist_tesis_punto = m_inicio + alpha * (m_fin - m_inicio)
                
                # Ajustar la distancia de la tesis a la escala real de Google Maps
                dist_maps_punto = dist_tesis_punto * factor_escala
                
                # Obtener coordenada Lat, Lon exacta sobre la curva
                lat, lon = interpolar_coordenada(dist_maps_punto, trazo_avenida, dist_acumuladas)
                
                # 5. Mitigación de Snapping y Validación Temporal mediante Metadata API
                meta = consultar_street_view_metadata(lat, lon, google_api_key)
                
                if meta.get("status") == "OK":
                    pano_id = meta.get("pano_id")
                    fecha_panorama = meta.get("date") # Obtenemos la fecha de Google
                    
                    # Ejecutamos la validación
                    es_valido, msj_validacion = validar_año_panorama(fecha_panorama, año_recoleccion)
                    
                    if not es_valido:
                        # Descartamos si no es del año que necesitamos
                        resultado_descargas.append({
                            "tramo_id": tramo_id,
                            "calzada": calzada_nombre,
                            "pci_clase": tramo["pci_clase"],
                            "pci_numérico": tramo["pci_numérico"],
                            "punto_sobremuestreo": j + 1,
                            "pano_id": pano_id,
                            "descargar": False,
                            "coordenada_calculada": [lat, lon],
                            "motivo": f"Descarte temporal: {msj_validacion}"
                        })
                        continue # Saltamos al siguiente punto

                    # Si pasa la validación de fecha, verificamos que no sea duplicado espacial
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
                            "pano_id": pano_id,
                            "fecha_real_google": fecha_panorama, # Guardamos la fecha exacta obtenida
                            "descargar": True
                        })
                    else:
                        # Se ignora la descarga para evitar duplicados en el dataset de IA
                        resultado_descargas.append({
                            "tramo_id": tramo_id,
                            "punto_sobremuestreo": j + 1,
                            "pano_id": pano_id,
                            "descargar": False,
                            "motivo": "Duplicado por Snapping"
                        })
                else:
                    print(f"     [!] Sin cobertura Street View en: {lat}, {lon}")
                    
    return resultado_descargas

if __name__ == "__main__":

    load_dotenv()
    
    # 1. Ruta al archivo de datos
    archivo_json = "prueba.json"
    API_KEY_GOOGLE = os.getenv("API_KEY_GOOGLE")
    
    # 2. Cargar el JSON desde el archivo
    try:
        with open(archivo_json, "r", encoding="utf-8") as f:
            datos_dataset = json.load(f)
            
        # Asumimos que el JSON puede ser una lista de proyectos o un objeto único.
        # Si es un solo proyecto, lo metemos en una lista para iterar.
        if isinstance(datos_dataset, dict):
            proyectos = [datos_dataset]
        else:
            proyectos = datos_dataset
            
        resultados_totales = []
        
        # 3. Procesar cada proyecto del archivo
        for proyecto in proyectos:
            print(f"\n--- Iniciando procesamiento de: {proyecto.get('proyecto_id', 'Sin ID')} ---")
            
            # Llamamos a tu función principal
            resultados_proyecto = procesar_proyecto_vial(proyecto, API_KEY_GOOGLE)
            resultados_totales.extend(resultados_proyecto)
            
        # 4. Guardar el archivo de salida consolidado
        with open("coor_UM_SanJuan.json", "w", encoding="utf-8") as archivo:
            json.dump(resultados_totales, archivo, indent=2, ensure_ascii=False)
            
        print(f"\n[ÉXITO] Se han procesado todos los proyectos.")
        print(f"Plan de descarga consolidado guardado en: 'coor_UM_SanJuan.json'")

    except FileNotFoundError:
        print(f"[ERROR] No se encontró el archivo '{archivo_json}'. Asegúrate de que esté en la misma carpeta.")
    except json.JSONDecodeError:
        print(f"[ERROR] El archivo '{archivo_json}' no tiene un formato JSON válido.")