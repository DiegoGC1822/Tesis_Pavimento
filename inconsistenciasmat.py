import numpy as np
import scipy.io

# 1. Cargar el archivo .mat original
datos = scipy.io.loadmat('gt.mat')
d = datos['d']

# 2. Extraer las columnas correspondientes (según el orden que vimos)
# Columna 2: puntuacion_original (índice 2)
# Columna 3: clase_original (índice 3)
segmento_id = d[:, 0]
cantidad_imagenes = d[:, 1]
puntuacion_original = d[:, 2]
clase_original = d[:, 3]


# 3. Definir la función para calcular la clase esperada
def calcular_clase_esperada(puntuacion):
  if 8 <= puntuacion <= 10:
    return 2  # Good
  elif 4 <= puntuacion <= 7:
    return 1  # Fair
  elif 1 <= puntuacion <= 3:
    return 0  # Poor
  else:
    return -1


# Calcular clases esperadas para todo el arreglo
clase_esperada = np.array([calcular_clase_esperada(p) for p in puntuacion_original])

# 4. Encontrar los índices donde la clase original difiere de la esperada
indices_inconsistentes = np.where(clase_original != clase_esperada)[0]

print(f'Total de inconsistencias encontradas en el .mat: {len(indices_inconsistentes)}')

# 5. Mostrar los primeros detalles si existen
if len(indices_inconsistentes) > 0:
  print('\nPrimeras filas inconsistentes en el archivo .mat:')
  print(
      'Índice (Python) | Segmento ID | Puntuación | Clase Original | Clase'
      ' Esperada'
  )
  print('-' * 70)

  for idx in indices_inconsistentes[:10]:  # Muestra los primeros 10
    print(
        f'{idx:15} | '
        f'{segmento_id[idx]:11} | '
        f'{puntuacion_original[idx]:10} | '
        f'{clase_original[idx]:14} | '
        f'{clase_esperada[idx]:14}'
    )

  if len(indices_inconsistentes) > 10:
    print(f'... y {len(indices_inconsistentes) - 10} casos más.')
else:
  print('¡Todo está correcto en el archivo .mat!')