import argparse
import json
import os
import sqlite3
import sys
from geopy.distance import geodesic
from dotenv import load_dotenv
from services import obtener_poliline_ruta
from utils import parametrizar_poliline, interpolar_coordenada, calcular_bearing, progresiva_a_metros

load_dotenv = load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

DB_PATH = os.path.join("App_ExtracciónCoor", "instance", "tesis_datos.db")
DATASET_PATH = "Dataset-UM-Avenidas.json"



def generar_referencias_espaciales(trazo_avenida, dist_acumuladas, longitud_total_maps, paso=2.0):
    """
    Genera puntos de referencia cada 'paso' (ej. 2 metros) sobre la polilínea real.
    Devuelve una lista de diccionarios con la distancia acumulada y su lat/lon.
    """
    referencias = []
    d = 0.0
    while d <= longitud_total_maps:
        lat, lon = interpolar_coordenada(d, trazo_avenida, dist_acumuladas)
        referencias.append({"dist_maps": d, "lat": lat, "lon": lon})
        d += paso
    return referencias

def proyectar_punto_a_progresiva(lat_db, lon_db, referencias):
    """
    Encuentra el punto de la polilínea más cercano al clic del usuario
    y retorna a qué distancia acumulada (en Google Maps) corresponde.
    """
    distancia_minima = float('inf')
    dist_acumulada_optima = 0.0

    for ref in referencias:
        dist = geodesic((lat_db, lon_db), (ref["lat"], ref["lon"])).meters
        if dist < distancia_minima:
            distancia_minima = dist
            dist_acumulada_optima = ref["dist_maps"]

    return dist_acumulada_optima


def generar_plan_avenida(proyecto: dict, puntos_db: dict, google_api_key: str) -> list:
    proyecto_id = proyecto["proyecto_id"]
    año_recoleccion = proyecto.get("año_recolección_imagen", proyecto.get("año_estudio"))
    longitud_total_tesis = proyecto.get("longitud_calzadas", 1000.0)
    resultado = []

    for calzada_nombre, calzada_info in proyecto["calzadas"].items():
        if calzada_info is None:
            continue

        puntos_calzada = puntos_db.get(calzada_nombre, [])
        tramos = calzada_info["tramos"]

        if not puntos_calzada:
            continue

        print(f"  Calzada '{calzada_nombre}': {len(puntos_calzada)} puntos → Mapeo Geográfico en {len(tramos)} tramos")

        # 1. Obtener geometría y calibración de la calzada
        coord_inicio = calzada_info["coordenadas_inicio_calzada"]
        coord_fin = calzada_info["coordenadas_fin_calzada"]
        offset_calzada = progresiva_a_metros(calzada_info.get("progresiva_inicio_calzada", "0+000"))
        
        trazo_avenida = obtener_poliline_ruta(coord_inicio, coord_fin, google_api_key)
        dist_acumuladas, longitud_total_maps = parametrizar_poliline(trazo_avenida)
        
        factor_escala = longitud_total_tesis / longitud_total_maps if longitud_total_maps > 0 else 1.0
        
        # 2. Generar marcadores virtuales cada 2 metros para proyección
        referencias = generar_referencias_espaciales(trazo_avenida, dist_acumuladas, longitud_total_maps)

        # 3. Diccionario para guardar los puntos asignados a cada tramo
        distribucion = {t["tramo_id"]: [] for t in tramos}
        
        # Procesar límites de cada tramo para búsqueda rápida
        limites_tramos = []
        for t in tramos:
            m_inicio = progresiva_a_metros(t["progresiva_inicio"]) - offset_calzada
            m_fin = progresiva_a_metros(t["progresiva_fin"]) - offset_calzada
            limites_tramos.append({
                "tramo_id": t["tramo_id"], 
                "inicio": m_inicio, 
                "fin": m_fin, 
                "info": t
            })

        # 4. Asignación Espacial: Proyectar cada punto de la DB
        TOLERANCIA_GPS_METROS = 5.0 
        
        for p in puntos_calzada:
            dist_maps_punto = proyectar_punto_a_progresiva(p["lat"], p["lon"], referencias)
            dist_tesis_punto = dist_maps_punto * factor_escala
            
            tramo_asignado = None
            distancia_minima_al_centro = float('inf')
            
            # Buscamos si el punto cae dentro de las fronteras (ampliadas por la tolerancia) de algún tramo
            for limite in limites_tramos:
                inicio_tolerado = limite["inicio"] - TOLERANCIA_GPS_METROS
                fin_tolerado = limite["fin"] + TOLERANCIA_GPS_METROS
                
                if inicio_tolerado <= dist_tesis_punto <= fin_tolerado:
                    # El punto cayó dentro de este tramo. 
                    # Calculamos qué tan al centro está por si hay solapamiento de tolerancias.
                    centro_tramo = (limite["inicio"] + limite["fin"]) / 2.0
                    dist_al_centro = abs(dist_tesis_punto - centro_tramo)
                    
                    if dist_al_centro < distancia_minima_al_centro:
                        distancia_minima_al_centro = dist_al_centro
                        tramo_asignado = limite["tramo_id"]
            
            if tramo_asignado:
                distribucion[tramo_asignado].append(p)
            else:
                # EL PUNTO CAYÓ EN UN HUECO (Zona no muestreada en la tesis)
                # Lo descartamos silenciosamente para que no contamine las UMs
                pass

        # --- A PARTIR DE AQUÍ EL CÓDIGO SE MANTIENE CASI IGUAL ---
        # Lista ordenada para calcular headings
        todos_puntos = []
        for tramo in tramos:
            todos_puntos.extend(distribucion[tramo["tramo_id"]])

        headings = []
        for idx, p in enumerate(todos_puntos):
            if idx < len(todos_puntos) - 1:
                sig = todos_puntos[idx + 1]
                h = calcular_bearing(p["lat"], p["lon"], sig["lat"], sig["lon"])
            else:
                h = headings[-1] if headings else 228.0
            headings.append(h)

        heading_map = {p["id"]: headings[i] for i, p in enumerate(todos_puntos)}
        pano_ids_vistos = set()
        
        # 5. Construcción del JSON final
        for limite in limites_tramos:
            tramo_id = limite["tramo_id"]
            pts_tramo = distribucion[tramo_id]
            info_tramo = limite["info"]

            for num_punto, p in enumerate(pts_tramo, start=1):
                h = heading_map[p["id"]]
                pano_id = p["pano_id"]

                if pano_id in pano_ids_vistos:
                    resultado.append({
                        "tramo_id": tramo_id,
                        "punto_sobremuestreo": num_punto,
                        "heading": h,
                        "pano_id": pano_id,
                        "descargar": False,
                        "motivo": "Duplicado por Snapping"
                    })
                else:
                    pano_ids_vistos.add(pano_id)
                    resultado.append({
                        "proyecto_id": proyecto_id,
                        "año_recolección_imagen": año_recoleccion,
                        "calzada": calzada_nombre,
                        "tramo_id": tramo_id,
                        "pci_clase": info_tramo["pci_clase"],
                        "pci_numérico": info_tramo["pci_numérico"],
                        "punto_sobremuestreo": num_punto,
                        "coordenada_calculada": [p["lat"], p["lon"]],
                        "heading": h,
                        "pano_id": pano_id,
                        "fecha_real_google": p["fecha"],
                        "descargar": True
                    })

    return resultado


# ── Carga de datos ─────────────────────────────────────────────────────────────

def cargar_dataset() -> dict:
    """Retorna índice {nombre_avenida: proyecto}."""
    if not os.path.exists(DATASET_PATH):
        print(f"[ERROR] No se encontró '{DATASET_PATH}'.")
        sys.exit(1)
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    proyectos = [data] if isinstance(data, dict) else data
    return {p["nombre_avenida"]: p for p in proyectos if "nombre_avenida" in p}


def cargar_puntos_db() -> dict:
    """
    Retorna { nombre_avenida: { sentido: [ {id, pano_id, lat, lon, fecha} ] } }
    Puntos ordenados por id (orden de inserción).
    """
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] No se encontró la base de datos en '{DB_PATH}'.")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT a.nombre AS nombre_avenida,
               p.id, p.pano_id, p.lat, p.lon, p.fecha, p.sentido
        FROM punto p
        JOIN avenida a ON a.id = p.avenida_id
        ORDER BY p.id ASC
    """)
    rows = cur.fetchall()
    conn.close()

    resultado: dict = {}
    for r in rows:
        resultado.setdefault(r["nombre_avenida"], {}).setdefault(r["sentido"], []).append({
            "id": r["id"],
            "pano_id": r["pano_id"],
            "lat": r["lat"],
            "lon": r["lon"],
            "fecha": r["fecha"],
        })
    return resultado


# ── Normalización flexible de nombres ─────────────────────────────────────────

def normalizar(s: str) -> str:
    return s.translate(str.maketrans("áéíóúÁÉÍÓÚñÑ", "aeiouAEIOUnN")).lower().strip()


def construir_matches(indice_dataset: dict, puntos_db: dict):
    """
    Empareja avenidas de la DB con proyectos del dataset (comparación flexible).
    Retorna (matches, sin_match).
    matches: [(nombre_db, nombre_ds, proyecto, puntos_sentidos)]
    """
    norm_dataset = {normalizar(k): k for k in indice_dataset}

    print("\n--- DEPURACIÓN DE NOMBRES ---")
    print("En el Dataset (JSON):", list(norm_dataset.keys()))
    print("En la Base de Datos:", [normalizar(k) for k in puntos_db.keys()])
    print("-----------------------------\n")
    
    matches, sin_match = [], []
    for nombre_db, puntos_sentidos in puntos_db.items():
        nd = normalizar(nombre_db)
        if nd in norm_dataset:
            nombre_ds = norm_dataset[nd]
            matches.append((nombre_db, nombre_ds, indice_dataset[nombre_ds], puntos_sentidos))
        else:
            sin_match.append(nombre_db)
    return matches, sin_match


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Genera planes de descarga desde tesis_datos.db + Dataset-UM-Avenidas.json. "
            "Sin argumentos procesa todas las avenidas con match."
        )
    )
    parser.add_argument(
        "-a", "--avenidas",
        nargs="*",
        default=None,
        metavar="NOMBRE",
        help=(
            "Nombres de avenida a procesar (según la DB o el dataset). "
            "Si se omite, se procesan todas con correspondencia."
        )
    )
    args = parser.parse_args()

    print(f"Cargando dataset: {DATASET_PATH}")
    indice_dataset = cargar_dataset()
    print(f"  {len(indice_dataset)} proyectos: {sorted(indice_dataset.keys())}")

    print(f"\nCargando puntos de BD: {DB_PATH}")
    puntos_db = cargar_puntos_db()
    print(f"  {len(puntos_db)} avenidas en DB: {sorted(puntos_db.keys())}")

    matches, sin_match = construir_matches(indice_dataset, puntos_db)

    if sin_match:
        print(f"\n[AVISO] Sin match en dataset (ignoradas): {sin_match}")

    # Filtro por argumento
    if args.avenidas:
        filtro = {normalizar(a) for a in args.avenidas}
        matches_filtrados = [m for m in matches if normalizar(m[0]) in filtro or normalizar(m[1]) in filtro]
        no_enc = [a for a in args.avenidas
                  if normalizar(a) not in {normalizar(m[0]) for m in matches}
                  and normalizar(a) not in {normalizar(m[1]) for m in matches}]
        if no_enc:
            print(f"\n[ERROR] No encontradas: {no_enc}")
            sys.exit(1)
        matches = matches_filtrados

    if not matches:
        print("\n[ERROR] No hay avenidas para procesar.")
        sys.exit(1)

    print(f"\nProcesando {len(matches)} avenida(s)...\n")

    for nombre_db, nombre_ds, proyecto, puntos_sentidos in matches:
        print(f"{'='*60}")
        print(f"  DB: '{nombre_db}'  →  Dataset: '{nombre_ds}'  ({proyecto['proyecto_id']})")
        print(f"{'='*60}")

        plan = generar_plan_avenida(proyecto, puntos_sentidos, GOOGLE_API_KEY)
        n_desc = sum(1 for r in plan if r.get("descargar"))

        nombre_archivo = f"plan_descarga_{nombre_ds.replace(' ', '_')}.json"
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)

        print(f"\n  [OK] {n_desc}/{len(plan)} para descarga → '{nombre_archivo}'\n")

    print(f"[FIN] {len(matches)} avenida(s) procesadas.")


if __name__ == "__main__":
    main()
