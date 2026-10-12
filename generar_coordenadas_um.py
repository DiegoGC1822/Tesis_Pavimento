import json
import os
from dotenv import load_dotenv
from services import obtener_poliline_ruta
from utils import parametrizar_poliline, interpolar_coordenada, progresiva_a_metros

load_dotenv()
API_KEY_GOOGLE = os.getenv("API_KEY_GOOGLE")

DATASET_PATH = "Dataset-UM-Avenidas.json"
OUTPUT_PATH = "Coor-UM-Avenidas.json"

AVENIDAS_OBJETIVO = ["13 de Enero", "Fernando Wiesse"]

def main():
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    resultados = []

    for proyecto in dataset:
        nombre = proyecto.get("nombre_avenida", "")
        if nombre not in AVENIDAS_OBJETIVO:
            continue
        
        print(f"Procesando avenida: {nombre}")
        
        longitud_total_tesis = proyecto.get("longitud_calzadas", 1000.0)
        
        nuevo_proyecto = proyecto.copy()
        nuevo_proyecto["calzadas"] = {}

        for calzada_nombre, calzada_info in proyecto.get("calzadas", {}).items():
            if calzada_info is None:
                nuevo_proyecto["calzadas"][calzada_nombre] = None
                continue
                
            coord_inicio = calzada_info["coordenadas_inicio_calzada"]
            coord_fin = calzada_info["coordenadas_fin_calzada"]
            offset_calzada = progresiva_a_metros(calzada_info.get("progresiva_inicio_calzada", "0+000"))
            
            trazo_avenida = obtener_poliline_ruta(coord_inicio, coord_fin, API_KEY_GOOGLE)
            dist_acumuladas, longitud_total_maps = parametrizar_poliline(trazo_avenida)
            
            factor_escala = longitud_total_tesis / longitud_total_maps if longitud_total_maps > 0 else 1.0
            
            nuevos_tramos = []
            for t in calzada_info["tramos"]:
                p_ini = t["progresiva_inicio"].replace("0.30.00", "30.00") if "0.30.00" in t["progresiva_inicio"] else t["progresiva_inicio"]
                p_fin = t["progresiva_fin"].replace("0.30.00", "30.00") if "0.30.00" in t["progresiva_fin"] else t["progresiva_fin"]

                m_inicio = progresiva_a_metros(p_ini) - offset_calzada
                m_fin = progresiva_a_metros(p_fin) - offset_calzada
                
                dist_maps_inicio = m_inicio / factor_escala
                dist_maps_fin = m_fin / factor_escala
                
                coord_inicio_um = interpolar_coordenada(dist_maps_inicio, trazo_avenida, dist_acumuladas)
                coord_fin_um = interpolar_coordenada(dist_maps_fin, trazo_avenida, dist_acumuladas)
                
                nuevo_tramo = t.copy()
                nuevo_tramo["coordenada_inicio_um"] = [coord_inicio_um[0], coord_inicio_um[1]]
                nuevo_tramo["coordenada_fin_um"] = [coord_fin_um[0], coord_fin_um[1]]
                
                nuevos_tramos.append(nuevo_tramo)
            
            nueva_calzada = calzada_info.copy()
            nueva_calzada["tramos"] = nuevos_tramos
            nuevo_proyecto["calzadas"][calzada_nombre] = nueva_calzada
            
        resultados.append(nuevo_proyecto)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    
    print(f"Archivo {OUTPUT_PATH} generado exitosamente.")

if __name__ == "__main__":
    main()
