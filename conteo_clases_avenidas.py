import pandas as pd

DATA_FILE = "data_all.csv"

def main():
    try:
        df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
    except Exception as e:
        print(f"Error al leer {DATA_FILE}: {e}")
        return

    # Generar tabla cruzada (conteo de clases por avenida)
    # pd.crosstab cuenta las frecuencias
    tabla = pd.crosstab(df['nombre_avenida'], df['pci_clase'])

    # Ordenar las columnas si existen en el dataframe
    columnas_deseadas = ['Good', 'Fair', 'Poor']
    columnas_presentes = [c for c in columnas_deseadas if c in tabla.columns]
    
    # Añadir columnas faltantes si por alguna razón no hay ninguna de esa clase
    for c in columnas_deseadas:
        if c not in tabla.columns:
            tabla[c] = 0

    # Reordenar
    tabla = tabla[columnas_deseadas]

    # Calcular la fila de totales
    tabla.loc['TOTAL'] = tabla.sum()

    # Mostrar por consola
    print("======================================================")
    print("        CONTEO DE CLASES POR AVENIDA")
    print("======================================================")
    print(tabla.to_string())
    print("======================================================")

    # Opcional: exportar a CSV para que lo puedas abrir en Excel
    tabla.to_csv("tabla_conteo_clases.csv", encoding="utf-8-sig")
    print("\nLa tabla también ha sido guardada en 'tabla_conteo_clases.csv'")

if __name__ == "__main__":
    main()
