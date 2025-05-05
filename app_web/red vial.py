import osmnx as ox

# Descargar la red vial de Celaya, Guanajuato, México (
G = ox.graph_from_place("Celaya, Guanajuato, Mexico", network_type='bike')

# Guardar el grafo en un archivo .graphml para usarlo más tarde
ox.save_graphml(G, "bike_celaya.graphml")

# visualizar la red vial con:
ox.plot_graph(G)
