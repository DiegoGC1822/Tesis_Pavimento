import pandas as pd

# 1. Cargar el archivo CSV (o puedes usar el DataFrame directamente si lo tienes en memoria)
df = pd.read_csv('data_support.csv')


# 2. Definir una función para calcular la clase que *debería* tener según la regla
def calcular_clase_esperada(puntuacion):
  if 8 <= puntuacion <= 10:
    return 2  # Good (Bueno)
  elif 4 <= puntuacion <= 7:
    return 1  # Fair (Regular)
  elif 1 <= puntuacion <= 3:
    return 0  # Poor (Malo / Pobre)
  else:
    return -1  # Fuera de rango


# 3. Aplicar la regla para crear una columna de control
df['clase_esperada'] = df['puntuacion_original'].apply(calcular_clase_esperada)

# 4. Filtrar las filas donde la clase original difiere de la clase esperada
inconsistencias = df[df['clase_original'] != df['clase_esperada']]

# 5. Mostrar los resultados
print(f'Total de inconsistencias encontradas: {len(inconsistencias)}')

if not inconsistencias.empty:
  print('\nDetalle de las filas con errores:')
  print(
      inconsistencias[
          [
              'segmento_id',
              'cantidad_imagenes',
              'puntuacion_original',
              'clase_original',
              'clase_esperada',
          ]
      ]
  )

  # Opcional: Guardar las inconsistencias en un archivo CSV independiente para revisarlas
  inconsistencias.to_csv('filas_con_errores.csv', index=False)
  print(
      '\nSe ha guardado un reporte de errores en el archivo'
      ' "filas_con_errores.csv".'
  )
else:
  print('¡Excelente! No se encontraron inconsistencias en los datos.')