import os
import json
import csv
import requests
from dotenv import load_dotenv

load_dotenv()

def descargar_y_registrar():
    # Configuración
    CARPETA_IMAGENES = "carpeta_imagenes"
    CARPETA_PLANES = "planes_descarga"
    ARCHIVO_CSV = "data.csv"
    PITCH = -24
    FOV = 22
    API_KEY = os.getenv("API_KEY_GOOGLE")

    os.makedirs(CARPETA_IMAGENES, exist_ok=True)

    # Preparar archivo CSV (modo 'w' borra el anterior cada vez que inicias)
    with open(ARCHIVO_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["nombre_imagen", "nombre_avenida", "calzada", "tramo_id", "pci_clase"])

    # Procesar archivos
    for archivo in os.listdir(CARPETA_PLANES):
        if archivo.endswith(".json"):
            nombre_avenida = archivo.replace("plan_descarga_", "").replace(".json", "")
            
            # --- EL PRINT AHORA VA AQUÍ (Solo una vez por avenida) ---
            print(f"--- Iniciando descarga de avenida: {nombre_avenida} ---")
            
            ruta_plan = os.path.join(CARPETA_PLANES, archivo)
            
            with open(ruta_plan, "r", encoding="utf-8") as f:
                plan = json.load(f)

            for punto in plan:
                if not punto.get("descargar", True):
                    continue

                pano_id = punto["pano_id"]
                
                # Definir direcciones
                direcciones = [
                    {"suffix": "adelante", "heading": punto["heading"]},
                    {"suffix": "atras", "heading": (punto["heading"] + 180) % 360}
                ]

                for d in direcciones:
                    nombre_img = f"{pano_id}_{d['suffix']}.jpg"
                    ruta_img = os.path.join(CARPETA_IMAGENES, nombre_img)
                    
                    # URL de descarga
                    url = (
                        f"https://maps.googleapis.com/maps/api/streetview?"
                        f"size=640x640&pano={pano_id}&heading={d['heading']}"
                        f"&pitch={PITCH}&fov={FOV}&key={API_KEY}"
                    )

                    try:
                        response = requests.get(url)
                        if response.status_code == 200:
                            with open(ruta_img, "wb") as handler:
                                handler.write(response.content)
                            
                            # Registrar en CSV (Abre y cierra en cada registro para que puedas ver el archivo)
                            with open(ARCHIVO_CSV, "a", newline="", encoding="utf-8") as f:
                                writer = csv.writer(f)
                                writer.writerow([
                                    nombre_img, nombre_avenida, punto["calzada"], 
                                    punto["tramo_id"], punto.get("pci_clase", "N/A")
                                ])
                    except Exception as e:
                        print(f"Error al descargar {nombre_img}: {e}")

    print("Proceso finalizado. Imágenes y CSV generados.")

if __name__ == "__main__":
    descargar_y_registrar()