from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017/")
print(client.list_database_names())  # Deberías ver 'caminaseguro' en la lista si hay datos
#loool