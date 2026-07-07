import os
import json
import requests
import math
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY_GOOGLE")

def descargar_imagen(pano_id, nombre_archivo, api_key, heading):
    """Descarga la imagen con un heading dinámico."""
    base_url = "https://maps.googleapis.com/maps/api/streetview"
    params = {
        "pano": pano_id,
        "heading": heading,
        "pitch": -24,  # Mirando al suelo
        "fov": 20,     # Zoom ajustado
        "size": "640x640",
        "key": api_key
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        with open(nombre_archivo, 'wb') as f:
            f.write(response.content)
        # print(f"✅ Guardado: {nombre_archivo} | Heading: {round(heading, 2)}")
    else:
        print(f"❌ Error {response.status_code} en {nombre_archivo}")

def ejecutar_prueba(json_path, cantidad=5):
    if not os.path.exists("imagenes_prueba"):
        os.makedirs("imagenes_prueba")

    with open(json_path, 'r') as f:
        data = json.load(f)

    candidatos = [item for item in data if item.get("descargar") is True]

    print(f"Total registros: {len(candidatos)}. Calculando ángulos y descargando...")

    for i, item in enumerate(candidatos[:cantidad]):
        # LÓGICA PARA EL HEADING DINÁMICO
        # Miramos si hay un siguiente punto en el mismo tramo para calcular el ángulo
        if item["heading"]:
            heading = item["heading"]
        else:
            # Si es el último punto del tramo, usamos el ángulo del anterior
            heading = 225 # Valor por defecto seguro

        pano_id = item["pano_id"]
        tramo = item["tramo_id"]
        punto = item['punto_sobremuestreo']

        # 1. Foto FRENTE (Mirando hacia el siguiente punto)
        descargar_imagen(pano_id, f"imagenes_prueba/{tramo}_p{punto}_frente.jpg", API_KEY, heading)
        
        # 2. Foto ATRÁS (Mirando hacia el lado opuesto)
        heading_atras = (heading + 180) % 360
        descargar_imagen(pano_id, f"imagenes_prueba/{tramo}_p{punto}_atras.jpg", API_KEY, heading_atras)
        
        print(f"✅ Tramo {tramo} Punto {punto} procesado (Heading: {round(heading, 1)}°)")

if __name__ == "__main__":
    ejecutar_prueba("plan_descarga_Nestor_Gambetta.json", cantidad=10)