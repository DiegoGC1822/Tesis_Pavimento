from geopy.distance import geodesic
import math

def progresiva_a_metros(progresiva_str):
    """Transforma una cadena tipo '1+035.4' a flotante en metros."""
    try:
        partes = progresiva_str.split('+')
        km = float(partes[0])
        m = float(partes[1]) if len(partes) > 1 else 0.0
        return (km * 1000.0) + m
    except Exception as e:
        raise ValueError(f"Error al parsear progresiva {progresiva_str}: {e}")

def parametrizar_poliline(coordenadas_lista):
    """Calcula las distancias acumuladas por cada vértice de la polilínea."""
    distancias_acumuladas = [0.0]
    dist_total = 0.0
    for i in range(len(coordenadas_lista) - 1):
        p1 = coordenadas_lista[i]
        p2 = coordenadas_lista[i+1]
        dist_segmento = geodesic(p1, p2).meters
        dist_total += dist_segmento
        distancias_acumuladas.append(dist_total)
    return distancias_acumuladas, dist_total

def interpolar_coordenada(distancia_objetivo, coord_lista, dist_acumuladas):
    """Encuentra la coordenada (Lat, Lon) exacta para una distancia acumulada dada."""
    if distancia_objetivo <= 0:
        return coord_lista[0]
    if distancia_objetivo >= dist_acumuladas[-1]:
        return coord_lista[-1]
    
    # Buscar el segmento
    for i in range(len(dist_acumuladas) - 1):
        if dist_acumuladas[i] <= distancia_objetivo <= dist_acumuladas[i+1]:
            d_ini = dist_acumuladas[i]
            d_fin = dist_acumuladas[i+1]
            # Fracción dentro del segmento
            fraction = (distancia_objetivo - d_ini) / (d_fin - d_ini)
            
            p1 = coord_lista[i]
            p2 = coord_lista[i+1]
            
            lat = p1[0] + fraction * (p2[0] - p1[0])
            lon = p1[1] + fraction * (p2[1] - p1[1])
            return (lat, lon)
    return coord_lista[-1]

def validar_año_panorama(fecha_google, año_objetivo):
    """
    Compara la fecha devuelta por la API con el año que exige la tesis.
    Google suele devolver 'YYYY-MM' o 'YYYY'.
    """
    if not fecha_google:
        return False, "Sin fecha disponible"
    
    # Extraemos solo los primeros 4 caracteres (el año)
    año_panorama = str(fecha_google)[:4]
    año_esperado = str(año_objetivo)
    
    if año_panorama == año_esperado:
        return True, "Año correcto"
    else:
        return False, f"Año incorrecto (Encontrado: {año_panorama}, Esperado: {año_esperado})"

def calcular_bearing(lat1, lon1, lat2, lon2):
    """
    Calcula el bearing (azimut) entre dos coordenadas.
    """
    # Convertir a radianes
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    dLon = lon2 - lon1
    
    x = math.sin(dLon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(dLon))
    
    initial_bearing = math.atan2(x, y)
    
    # Convertir a grados y normalizar (0 a 360)
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360
    
    return compass_bearing