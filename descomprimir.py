import shutil
import zipfile
from pathlib import Path

# ====== CONFIGURACIÓN ======
BASE_DIR = Path("imagenes_nuevas")   # ajusta la ruta si es necesario
DESDE, HASTA = 25,72
BORRAR_ZIP = True                  # True para borrar el zip tras extraer con éxito
# ===========================


def descender_carpetas_unicas(carpeta: Path) -> Path:
    """Mientras la carpeta contenga solo UNA subcarpeta y nada más, entra en ella."""
    while True:
        items = list(carpeta.iterdir())
        if len(items) == 1 and items[0].is_dir():
            carpeta = items[0]
        else:
            return carpeta


def procesar_zip(numero: int) -> None:
    zip_path = BASE_DIR / f"{numero}.zip"
    destino = BASE_DIR / str(numero)
    temp = BASE_DIR / f"_tmp_{numero}"

    if not zip_path.exists():
        print(f"[{numero}] No existe {zip_path.name}, se omite.")
        return

    if destino.exists() and any(destino.iterdir()):
        print(f"[{numero}] {destino} ya tiene contenido, se omite.")
        return

    try:
        # 1. Extraer a carpeta temporal
        if temp.exists():
            shutil.rmtree(temp)
        temp.mkdir(parents=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(temp)

        # 2. Quitar carpetas anidadas redundantes (22/22/...)
        origen = descender_carpetas_unicas(temp)

        # 3. Mover contenido al destino final
        destino.mkdir(exist_ok=True)
        for item in origen.iterdir():
            shutil.move(str(item), str(destino / item.name))

        n = sum(1 for p in destino.iterdir() if p.is_file())
        print(f"[{numero}] OK -> {destino} ({n} archivos)")

        if BORRAR_ZIP:
            zip_path.unlink()

    except zipfile.BadZipFile:
        print(f"[{numero}] ERROR: zip corrupto.")
    except Exception as e:
        print(f"[{numero}] ERROR: {e}")
    finally:
        if temp.exists():
            shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    for n in range(DESDE, HASTA + 1):
        procesar_zip(n)
    print("Listo.")