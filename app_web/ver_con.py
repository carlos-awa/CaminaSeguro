from pymongo import MongoClient
client = MongoClient("mongodb+srv://caminaseguro:bWbTAwKWxEFzgfQt@cluster0.oawj7sa.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
print(client.list_database_names())  # Deberías ver 'caminaseguro' en la lista