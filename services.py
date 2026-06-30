import requests
import polyline

def obtener_poliline_ruta(inicio_coords, fin_coords, api_key):
    """
    Consume la Directions API de Google para obtener el trazo real de la calle.
    (Simulado si no hay API Key para desarrollo local).
    """
    if not api_key or api_key == "TU_API_KEY":
        # Simulación de una polilínea con puntos intermedios simulados para pruebas
        print("[INFO] Usando trazo interpolado simulado (Desarrollo).")
        puntos_simulados = []
        pasos = 20
        for i in range(pasos + 1):
            alpha = i / pasos
            lat = inicio_coords[0] + alpha * (fin_coords[0] - inicio_coords[0])
            lon = inicio_coords[1] + alpha * (fin_coords[1] - inicio_coords[1])
            puntos_simulados.append((lat, lon))
        return puntos_simulados

    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{inicio_coords[0]},{inicio_coords[1]}",
        "destination": f"{fin_coords[0]},{fin_coords[1]}",
        "mode": "walking",
        "key": api_key
    }
    response = requests.get(url, params=params).json()
    points = response['routes'][0]['overview_polyline']['points']
    return polyline.decode(points)

def consultar_street_view_metadata(lat, lon, api_key):
    """Consulta la Metadata API para verificar existencia y obtener el pano_id."""
    if not api_key or api_key == "TU_API_KEY":
        # Simulación de respuesta API
        return {"status": "OK", "pano_id": f"mock_pano_{round(lat,4)}_{round(lon,4)}", "date": "2024-08"}
        
    url = "https://maps.googleapis.com/maps/api/streetview/metadata"
    params = {"location": f"{lat},{lon}", "key": api_key}
    try:
        res = requests.get(url, params=params).json()
        return res
    except Exception:
        return {"status": "UNKNOWN"}