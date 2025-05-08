import json
import difflib
from collections import defaultdict

# --- Funciones de apoyo ---

def normalizar_nombre(nombre):
    nombre = nombre.lower().strip()
    for prefijo in ["calle", "av.", "avenida", "andador", "privada"]:
        if nombre.startswith(prefijo):
            nombre = nombre.replace(prefijo, "", 1).strip()
    return nombre.title()

def redondear_coords(coords):
    # Redondeo para agrupar puntos cercanos (~1.1 m)
    return (round(coords[0], 5), round(coords[1], 5))

def agrupar_nombres_similares(nombres):
    grupos = []
    usados = set()
    for i, nombre in enumerate(nombres):
        if i in usados:
            continue
        grupo = [nombre]
        for j, otro in enumerate(nombres[i+1:], start=i+1):
            if j in usados:
                continue
            if difflib.SequenceMatcher(None, nombre, otro).ratio() > 0.85:
                grupo.append(otro)
                usados.add(j)
        grupos.append(grupo)
    # Retornar el nombre más largo y representativo de cada grupo
    nombre_final = max(grupos[0], key=len) if grupos else ""
    return nombre_final

# --- Cargar datos JSON ---

with open("delitos json/incidentes_unificados.json", "r", encoding="utf-8") as f:
    datos = json.load(f)

# --- Agrupación por coordenadas redondeadas ---

agrupados = defaultdict(list)

for item in datos:
    coords = redondear_coords(item["ubicacion"]["coordinates"])
    calle = normalizar_nombre(item.get("calle", ""))
    colonia = normalizar_nombre(item.get("colonia", ""))

    item["_calle_normalizada"] = calle
    item["_colonia_normalizada"] = colonia
    agrupados[coords].append(item)

# --- Corregir nombres similares por coordenadas ---

datos_corregidos = []

for grupo in agrupados.values():
    calles = [d["_calle_normalizada"] for d in grupo if d["_calle_normalizada"]]
    colonias = [d["_colonia_normalizada"] for d in grupo if d["_colonia_normalizada"]]

    calle_final = agrupar_nombres_similares(calles)
    colonia_final = agrupar_nombres_similares(colonias)

    for d in grupo:
        d["calle"] = calle_final
        d["colonia"] = colonia_final
        del d["_calle_normalizada"]
        del d["_colonia_normalizada"]
        datos_corregidos.append(d)

# --- Guardar resultado ---

with open("delitos json/delitos_corregidos.json", "w", encoding="utf-8") as f:
    json.dump(datos_corregidos, f, indent=2, ensure_ascii=False)

print(f"✔ Se corrigieron {len(datos_corregidos)} registros. Guardado en 'delitos_corregidos.json'.")
