import os
import json
import pandas as pd
import unicodedata

def normalize_text(text):
    text = str(text)
    # Remove accents, replace ñ with n, lower case, remove spaces and underscores
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    return text.lower().replace("_", "").replace(" ", "").replace("-", "")

def normalize_tramo(tramo):
    return str(tramo).upper().replace("-", "").strip()

def main():
    CARPETA_PLANES = "planes_descarga_PxVP"
    DATA_FILE = "data_audiGood_PxVP.csv"
    
    # 1. Crear el mapeo
    # tramo_a_clase[avenida_norm][tramo_norm] = pci_clase
    tramo_a_clase = {}
    
    for archivo in os.listdir(CARPETA_PLANES):
        if not archivo.endswith(".json"):
            continue
        
        # Extraer nombre avenida de filename, por ejemplo "plan_descarga_Marañon.json"
        # Quitamos "plan_descarga_" y ".json"
        avenida_name = archivo.replace("plan_descarga_", "").replace(".json", "")
        avenida_norm = normalize_text(avenida_name)
        
        if avenida_norm not in tramo_a_clase:
            tramo_a_clase[avenida_norm] = {}
            
        ruta_plan = os.path.join(CARPETA_PLANES, archivo)
        with open(ruta_plan, "r", encoding="utf-8") as f:
            plan = json.load(f)
            for punto in plan:
                tramo_id_json = punto.get("tramo_id", "")
                tramo_key = normalize_tramo(tramo_id_json)
                pci_clase = punto.get("pci_clase")
                if tramo_key and pci_clase:
                    tramo_a_clase[avenida_norm][tramo_key] = pci_clase
                    
    # 2. Actualizar data copy.csv
    try:
        df = pd.read_csv(DATA_FILE, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(DATA_FILE, encoding="latin1")
        
    def get_nueva_clase(row):
        avenida_csv = str(row["nombre_avenida"])
        avenida_norm = normalize_text(avenida_csv)
        
        tramo_csv = str(row["tramo_id"])
        tramo_key = normalize_tramo(tramo_csv)
        
        if avenida_norm in tramo_a_clase:
            if tramo_key in tramo_a_clase[avenida_norm]:
                return tramo_a_clase[avenida_norm][tramo_key]
        
        return row["pci_clase"] # fallback si no lo encuentra
        
    df["pci_clase"] = df.apply(get_nueva_clase, axis=1)
    
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
    print("Se actualizaron las clases en", DATA_FILE)

if __name__ == "__main__":
    main()
