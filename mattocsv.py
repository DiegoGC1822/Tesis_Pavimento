import pandas as pd
import scipy.io

# 1. Cargar el archivo .mat
datos = scipy.io.loadmat('gt.mat')

# 2. Obtener la variable 'd'
d = datos['d']

# 3. Ver sus dimensiones y tipo de datos
print('Forma (shape) de d:', d.shape)
print('Tipo de dato:', type(d))

# 4. Crear el DataFrame y asignar los encabezados personalizados
df = pd.DataFrame(
    d,
    columns=[
        'segmento_id',
        'cantidad_imagenes',
        'puntuacion_original',
        'clase_original',
    ],
)

# 5. Guardar como CSV incluyendo los encabezados
df.to_csv('data_support.csv', index=False, header=True)
print('¡Archivo data_support.csv creado con éxito con sus encabezados!')