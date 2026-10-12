"""
retorno_clases.py
-----------------
Compara la columna `pci_clase` entre los archivos de splits (train.csv,
test.csv, val.csv) y data_new.csv.  Reporta únicamente las filas donde
la clase difiere, indicando:
  - nombre_imagen
  - archivo de origen (train / test / val)
  - pci_clase en el split
  - pci_clase en data_new.csv

NO modifica ningún archivo.
"""

import pandas as pd
from pathlib import Path

# ── Rutas ──────────────────────────────────────────────────────────────
SPLITS_DIR = Path(
    r"C:\Users\Diego\Desktop\Tesis_Pavimento"
    r"\resultados_resnet50_tesis2\20261012T062252051485Z_224\splits"
)
DATA_NEW_PATH = Path(
    r"C:\Users\Diego\Desktop\Tesis_Pavimento\data_final_v4.csv"
)

# ── Cargar data_new ────────────────────────────────────────────────────
data_new = pd.read_csv(DATA_NEW_PATH)
# Crear diccionario {nombre_imagen: pci_clase} para búsqueda rápida
data_new_map = dict(
    zip(data_new["nombre_imagen"], data_new["pci_clase"])
)

# ── Recorrer cada split ───────────────────────────────────────────────
split_files = ["train.csv", "test.csv", "val.csv"]
diferencias = []

for split_file in split_files:
    split_path = SPLITS_DIR / split_file
    if not split_path.exists():
        print(f"⚠  No se encontró {split_path}")
        continue

    df = pd.read_csv(split_path)

    for _, row in df.iterrows():
        img = row["nombre_imagen"]
        clase_split = str(row["pci_clase"]).strip()

        if img not in data_new_map:
            diferencias.append({
                "nombre_imagen": img,
                "archivo_split": split_file,
                "pci_clase_split": clase_split,
                "pci_clase_data_new": "** NO ENCONTRADA EN data_new **",
            })
            continue

        clase_new = str(data_new_map[img]).strip()

        if clase_split != clase_new:
            diferencias.append({
                "nombre_imagen": img,
                "archivo_split": split_file,
                "pci_clase_split": clase_split,
                "pci_clase_data_new": clase_new,
            })

# ── Reporte ───────────────────────────────────────────────────────────
print("=" * 80)
print("REPORTE DE DIFERENCIAS EN pci_clase  (splits vs data_new)")
print("=" * 80)

if not diferencias:
    print("\n✅  No se encontraron diferencias. Todos los valores coinciden.")
else:
    print(f"\nSe encontraron {len(diferencias)} diferencia(s):\n")
    for i, d in enumerate(diferencias, start=1):
        print(f"  {i:>4}. {d['nombre_imagen']}")
        print(f"        {d['archivo_split']:>10}: {d['pci_clase_split']}")
        print(f"        {'data_new':>10}: {d['pci_clase_data_new']}")
        print()

print("=" * 80)
print("Fin del reporte.")
