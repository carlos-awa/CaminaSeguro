import json

with open("delitos json/delitos_corregidos.json", "r", encoding="utf-8") as f:
    contenido = f.read()
    json.loads(contenido)  # Lanza error si el JSON no es válido
