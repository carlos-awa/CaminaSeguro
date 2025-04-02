import json
import numpy as np

# 1. Leer el archivo JSON original
with open('incidentes_unificados.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 2. Función para limpiar NaN recursivamente
def clean_nan(obj):
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items() if v is not None and not (isinstance(v, float) and np.isnan(v))}
    elif isinstance(obj, list):
        return [clean_nan(item) for item in obj if item is not None and not (isinstance(item, float) and np.isnan(item))]
    else:
        return obj if not (isinstance(obj, float) and np.isnan(obj)) else ""

# 3. Limpiar los datos
cleaned_data = clean_nan(data)

# 4. Guardar el nuevo archivo JSON limpio
with open('incidentes_limpios.json', 'w', encoding='utf-8') as f:
    json.dump(cleaned_data, f, indent=2, ensure_ascii=False)

print("✅ JSON limpiado guardado como 'incidentes_limpios.json'")
print(f"Documentos originales: {len(data)} | Documentos limpios: {len(cleaned_data)}")