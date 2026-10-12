"""
Script para encontrar imágenes faltantes en data_final.csv
y generar data_discard.csv con la data mapeada desde planes_descarga_Poorx4.
Luego une ambos datasets en data_all.csv.
"""
import os
import json
import pandas as pd
import re

# --- Configuración ---
CARPETA_IMAGENES = "carpeta_imagenes"
IMAGENES_DESCARTADAS = "imagenes_descartadas"
PLANES_FOLDER = "planes_descarga_Poorx4"
DATA_CSV = "data_final.csv"
OUTPUT_DISCARD = "data_discard.csv"
OUTPUT_ALL = "data_all.csv"

# --- Paso 1: Leer data.csv existente ---
df_existing = pd.read_csv(DATA_CSV, encoding="utf-8-sig")
existing_images = set(df_existing["nombre_imagen"].str.strip().values)
print(f"[INFO] data.csv tiene {len(df_existing)} registros ({len(existing_images)} imágenes únicas)")

# --- Paso 2: Obtener TODAS las imágenes de ambas carpetas ---
all_image_files = set()

# Imágenes en carpeta_imagenes
for f in os.listdir(CARPETA_IMAGENES):
    if f.lower().endswith(('.jpg', '.jpeg', '.png')):
        all_image_files.add(f)
print(f"[INFO] carpeta_imagenes tiene {len([f for f in os.listdir(CARPETA_IMAGENES) if f.lower().endswith(('.jpg','.jpeg','.png'))])} imágenes")

# Imágenes en imagenes_descartadas
for f in os.listdir(IMAGENES_DESCARTADAS):
    if f.lower().endswith(('.jpg', '.jpeg', '.png')):
        all_image_files.add(f)
print(f"[INFO] imagenes_descartadas tiene {len([f for f in os.listdir(IMAGENES_DESCARTADAS) if f.lower().endswith(('.jpg','.jpeg','.png'))])} imágenes")

print(f"[INFO] Total de imágenes en disco: {len(all_image_files)}")

# --- Paso 3: Encontrar imágenes que NO están en data.csv ---
missing_images = all_image_files - existing_images
print(f"[INFO] Imágenes faltantes en data.csv: {len(missing_images)}")

# --- Paso 4: Construir mapeo pano_id -> metadata desde planes_descarga_3_clases ---
# Cada plan tiene: pano_id, calzada, tramo_id, pci_clase
# El nombre_avenida se extrae del nombre del archivo del plan
pano_to_metadata = {}

for plan_file in os.listdir(PLANES_FOLDER):
    if not plan_file.endswith(".json"):
        continue
    
    # Extraer nombre_avenida del nombre del archivo
    # plan_descarga_Bertello.json -> Bertello
    nombre_avenida = plan_file.replace("plan_descarga_", "").replace(".json", "")
    
    ruta_plan = os.path.join(PLANES_FOLDER, plan_file)
    with open(ruta_plan, "r", encoding="utf-8") as f:
        plan_data = json.load(f)
    
    for entry in plan_data:
        pano_id = entry.get("pano_id", "")
        if not pano_id:
            continue
        
        # Solo guardar si tiene los campos necesarios
        metadata = {
            "nombre_avenida": nombre_avenida,
            "calzada": entry.get("calzada", ""),
            "tramo_id": entry.get("tramo_id", ""),
            "pci_clase": entry.get("pci_clase", ""),
        }
        
        # Si el pano_id ya existe, no sobreescribir (el primer match es válido)
        if pano_id not in pano_to_metadata:
            pano_to_metadata[pano_id] = metadata

print(f"[INFO] Mapeo de planes construido: {len(pano_to_metadata)} pano_ids únicos")

# --- Paso 5: Mapear imágenes faltantes a su metadata ---
discard_rows = []
not_found_pano_ids = []

for img_name in sorted(missing_images):
    # Extraer pano_id del nombre de imagen
    # Formato: {pano_id}_adelante.jpg o {pano_id}_atras.jpg
    match = re.match(r"^(.+?)_(adelante|atras)\.(jpg|jpeg|png)$", img_name, re.IGNORECASE)
    if match:
        pano_id = match.group(1)
    else:
        # Fallback: quitar extensión
        pano_id = os.path.splitext(img_name)[0]
    
    if pano_id in pano_to_metadata:
        meta = pano_to_metadata[pano_id]
        discard_rows.append({
            "nombre_imagen": img_name,
            "nombre_avenida": meta["nombre_avenida"],
            "calzada": meta["calzada"],
            "tramo_id": meta["tramo_id"],
            "pci_clase": meta["pci_clase"],
        })
    else:
        not_found_pano_ids.append((img_name, pano_id))

print(f"[INFO] Imágenes mapeadas exitosamente: {len(discard_rows)}")
if not_found_pano_ids:
    print(f"[WARN] Imágenes SIN mapeo en planes ({len(not_found_pano_ids)}):")
    for img, pid in not_found_pano_ids[:20]:
        print(f"  - {img} (pano_id: {pid})")
    if len(not_found_pano_ids) > 20:
        print(f"  ... y {len(not_found_pano_ids) - 20} más")

# --- Paso 6: Crear data_discard.csv ---
df_discard = pd.DataFrame(discard_rows, columns=["nombre_imagen", "nombre_avenida", "calzada", "tramo_id", "pci_clase"])
df_discard.to_csv(OUTPUT_DISCARD, index=False, encoding="utf-8-sig")
print(f"\n[OK] Archivo '{OUTPUT_DISCARD}' creado con {len(df_discard)} registros")

# --- Paso 7: Unir data existente + descartada en data_all.csv ---
df_all = pd.concat([df_existing, df_discard], ignore_index=True)
df_all.to_csv(OUTPUT_ALL, index=False, encoding="utf-8-sig")
print(f"[OK] Archivo '{OUTPUT_ALL}' creado con {len(df_all)} registros totales")
print(f"     ({len(df_existing)} existentes + {len(df_discard)} descartados)")

# --- Resumen final ---
print(f"\n{'='*60}")
print(f"RESUMEN:")
print(f"  data.csv original:        {len(df_existing)} registros")
print(f"  data_discard.csv nuevo:   {len(df_discard)} registros")
print(f"  data_all.csv combinado:   {len(df_all)} registros")
print(f"  Sin mapeo en planes:      {len(not_found_pano_ids)} imágenes")
print(f"{'='*60}")
