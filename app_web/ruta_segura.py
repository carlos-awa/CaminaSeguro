from flask import Flask, jsonify, request
from flask_cors import CORS
import osmnx as ox
import networkx as nx
import requests
import logging

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# Cargar grafos
print("Cargando grafos...")
G_walk = ox.load_graphml('walk_celaya.graphml')
G_drive = ox.load_graphml('drive_celaya.graphml')
G_bike = ox.load_graphml('bike_celaya.graphml')

# Cargar peligrosidad
print("Cargando peligrosidad...")
calles_data = requests.get("http://localhost:5000/api/calles").json()
calles = calles_data.get("data", [])

peligrosidad_por_calle = {
    c["calle"].strip().lower(): c["nivel_peligro"]
    for c in calles if c.get("calle")
}

def asignar_pesos(G):
    for u, v, k, data in G.edges(keys=True, data=True):
        name = data.get("name")
        if not name:
            data["weight"] = data.get("length", 1)
            continue

        if isinstance(name, list): name = name[0]
        name_lower = name.strip().lower()
        peligro = peligrosidad_por_calle.get(name_lower, "Bajo")

        factor = {"Bajo": 1, "Medio": 2, "Alto": 5}.get(peligro, 1)
        data["weight"] = data.get("length", 1) * factor

# Asignar pesos
asignar_pesos(G_walk)
asignar_pesos(G_drive)
asignar_pesos(G_bike)

# Ruta base
def calcular_ruta(G, origen_lat, origen_lon, destino_lat, destino_lon, modo):
    nodo_origen = ox.distance.nearest_nodes(G, origen_lon, origen_lat)
    nodo_destino = ox.distance.nearest_nodes(G, destino_lon, destino_lat)

    ruta = nx.shortest_path(G, nodo_origen, nodo_destino, weight='weight')

    coordenadas = []
    distancia_total = 0

    for i in range(len(ruta) - 1):
        u, v = ruta[i], ruta[i + 1]
        edge_data = G.get_edge_data(u, v) or G.get_edge_data(v, u)
        if not edge_data:
            continue
        edge = list(edge_data.values())[0]
        distancia = edge.get('length', 0)
        distancia_total += distancia

        if 'geometry' in edge:
            coords = list(edge['geometry'].coords)
        else:
            coords = [(G.nodes[u]['x'], G.nodes[u]['y']), (G.nodes[v]['x'], G.nodes[v]['y'])]
        coordenadas.extend(coords)

    # Velocidades promedio por modo (m/s)
    velocidades = {"peatonal": 1.4, "bicicleta": 4.5, "vehículo": 13.8}
    velocidad = velocidades.get(modo, 1.4)
    tiempo_estimado = distancia_total / velocidad  # en segundos

    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coordenadas
        },
        "properties": {
            "descripcion": f"Ruta más segura ({modo})",
            "distancia_m": distancia_total,
            "tiempo_s": tiempo_estimado
        }
    }

# Endpoint para peatones
@app.route('/ruta_segura_walk', methods=['GET'])
def ruta_walk():
    try:
        lat_o = float(request.args.get('origen_lat'))
        lon_o = float(request.args.get('origen_lon'))
        lat_d = float(request.args.get('destino_lat'))
        lon_d = float(request.args.get('destino_lon'))

        geojson = calcular_ruta(G_walk, lat_o, lon_o, lat_d, lon_d, "peatonal")
        return jsonify(geojson)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint para vehículos
@app.route('/ruta_segura_drive', methods=['GET'])
def ruta_drive():
    try:
        lat_o = float(request.args.get('origen_lat'))
        lon_o = float(request.args.get('origen_lon'))
        lat_d = float(request.args.get('destino_lat'))
        lon_d = float(request.args.get('destino_lon'))

        geojson = calcular_ruta(G_drive, lat_o, lon_o, lat_d, lon_d, "vehículo")
        return jsonify(geojson)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint para bicicletas
@app.route('/ruta_segura_bike', methods=['GET'])
def ruta_bike():
    try:
        lat_o = float(request.args.get('origen_lat'))
        lon_o = float(request.args.get('origen_lon'))
        lat_d = float(request.args.get('destino_lat'))
        lat_d = float(request.args.get('destino_lat'))
        lon_d = float(request.args.get('destino_lon'))

        geojson = calcular_ruta(G_bike, lat_o, lon_o, lat_d, lon_d, "bicicleta")
        return jsonify(geojson)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5050, debug=True)
