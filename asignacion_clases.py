import os 
import json

def cambio_clases():
    CARPETA_PLANES = "planes_descarga_nuevo"

    for archivo in os.listdir(CARPETA_PLANES):
        ruta_plan = os.path.join(CARPETA_PLANES, archivo)
            
        with open(ruta_plan, "r", encoding="utf-8") as f:
            plan = json.load(f)

        for punto in plan:
            try:
                pci = punto.get("pci_numérico")
                if pci is None:
                    continue
                val = float(pci) if isinstance(pci, str) else pci
                if val > 70:
                    punto["pci_clase"] = "Good"
                elif val > 55:
                    punto["pci_clase"] = "Fair"
                else:
                    punto["pci_clase"] = "Poor"
            except (ValueError, TypeError):
                pass
        
        with open(ruta_plan, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)


if __name__ == "__main__":
    cambio_clases()
        