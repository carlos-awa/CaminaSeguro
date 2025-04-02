import pandas as pd
import json
from datetime import datetime
import os

# Configuración
ARCHIVOS_CSV = [
    "coordenadas csv/2020_coordenadas.csv",
    "coordenadas csv/2021_coordenadas.csv",
    "coordenadas csv/2022_coordenadas.csv",
    "coordenadas csv/2023_coordenadas.csv",
    "coordenadas csv/2024_coordenadas.csv",
    "coordenadas csv/2025_coordenadas.csv"
]
OUTPUT_JSON = "incidentes_unificados.json"

# Diccionario de meses (español -> inglés)
meses_es_to_en = {
    'ENERO': 'January', 'FEBRERO': 'February', 'MARZO': 'March',
    'ABRIL': 'April', 'MAYO': 'May', 'JUNIO': 'June',
    'JULIO': 'July', 'AGOSTO': 'August', 'SEPTIEMBRE': 'September',
    'OCTUBRE': 'October', 'NOVIEMBRE': 'November', 'DICIEMBRE': 'December'
}


def procesar_csv(ruta_csv):
    """Carga un CSV y devuelve una lista de documentos para MongoDB"""
    df = pd.read_csv(ruta_csv)
    documentos = []

    for _, row in df.iterrows():
        try:
            # Construir fecha (maneja errores si el formato cambia)
            fecha = datetime(
                int(row["anio"]),
                datetime.strptime(meses_es_to_en[row["mes_nombre"].upper()], "%B").month,
                int(row["dia"])
            ) if "mes_nombre" in row and pd.notna(row["mes_nombre"]) else None
        except:
            fecha = None

        doc = {
            "delito": row["delito"],
            "municipio": row["municipio"],
            "anio": int(row["anio"]),
            "mes_nombre": row.get("mes_nombre", ""),
            "dia": int(row["dia"]),
            "colonia": row["colonia"],
            "calle": row["calle"],
            "forma_accion": row["forma_accion"],
            "ubicacion": {
                "type": "Point",
                "coordinates": [float(row["longitud"]), float(row["latitud"])]
            },
            "fecha_completa": fecha
        }
        documentos.append(doc)

    return documentos


# Procesar todos los archivos
documentos_totales = []
for csv in ARCHIVOS_CSV:
    print(f"Procesando: {csv}...")
    documentos_totales += procesar_csv(csv)

# Guardar en un único JSON
with open(OUTPUT_JSON, "w", encoding='utf-8') as f:
    json.dump(documentos_totales, f, indent=2, ensure_ascii=False, default=str)

print(f"✅ ¡Se han procesado {len(documentos_totales)} registros en {OUTPUT_JSON}!")