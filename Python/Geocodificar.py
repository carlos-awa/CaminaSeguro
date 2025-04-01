import pandas as pd
import requests
import concurrent.futures
from threading import Lock
import os
import json

# Configuración
API_KEY = ""  # Reemplázala con tu API Key
INPUT_CSV = "delitos csv/2020.csv"
OUTPUT_CSV = "2020_coordenadas.csv"
CACHE_FILE = "cache_coordenadas.json"  # Archivo para guardar direcciones procesadas

# Cargar cache existente o crear uno nuevo
cache = {}
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, 'r') as f:
        cache = json.load(f)

# Lock para evitar conflictos al escribir en el cache
cache_lock = Lock()


def geocode_google(calle, colonia):
    clave = f"{calle}_{colonia}".strip().lower()

    # Revisar cache primero
    if clave in cache:
        return cache[clave]

    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={calle}, {colonia}, Celaya, México&key={API_KEY}"
        response = requests.get(url, timeout=10).json()

        if response.get('results'):
            loc = response['results'][0]['geometry']['location']
            resultado = (loc['lng'], loc['lat'])

            # Guardar en cache
            with cache_lock:
                cache[clave] = resultado
                with open(CACHE_FILE, 'w') as f:
                    json.dump(cache, f)

            return resultado
        return (None, None)
    except Exception as e:
        print(f"Error en {calle}, {colonia}: {str(e)}")
        return (None, None)


# Leer datos
df = pd.read_csv(INPUT_CSV)


# Función para procesar cada fila
def procesar_fila(row):
    calle, colonia = row['calle'], row['colonia']
    return geocode_google(calle, colonia)


# Procesamiento paralelo
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    # Usar map para mantener orden original
    resultados = list(executor.map(procesar_fila, [row for _, row in df.iterrows()]))

# Asignar resultados al DataFrame
df[['longitud', 'latitud']] = resultados

# Guardar resultados finales
df.to_csv(OUTPUT_CSV, index=False)
print(f"Proceso completado. Datos guardados en {OUTPUT_CSV}")
print(f"Total direcciones procesadas: {len(df)}")
print(f"Direcciones desde cache: {len([x for x in resultados if x in cache.values()])}")