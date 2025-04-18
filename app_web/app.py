from flask import Flask, render_template, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()  # Carga variables de entorno

app = Flask(__name__)
client = MongoClient("mongodb+srv://caminaseguro:bWbTAwKWxEFzgfQt@cluster0.oawj7sa.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client.caminaseguro

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/crear-ejemplo', methods=['GET'])
def crear_ejemplo():
    datos_ejemplo = [
        {
            "municipio": "CELAYA",
            "colonia": "Centro",
            "ubicacion": {
                "type": "Point",
                "coordinates": [-100.814, 20.524]
            },
            "delito": "Robo"
        },
        {
            "municipio": "Celaya",
            "colonia": "San Juanico",
            "ubicacion": {
                "type": "Point",
                "coordinates": [-100.815, 20.525]
            },
            "delito": "Vandalismo"
        }
    ]

    try:
        # Eliminar documentos existentes primero (opcional)
        db.delitos.delete_many({})

        # Insertar nuevos documentos
        result = db.delitos.insert_many(datos_ejemplo)

        # Convertir ObjectIds a strings para la respuesta JSON
        inserted_ids = [str(id) for id in result.inserted_ids]

        # Obtener los documentos insertados para mostrarlos
        docs_insertados = list(db.delitos.find({"_id": {"$in": result.inserted_ids}}))

        # Función para limpiar el documento antes de serializar
        def limpiar_doc(doc):
            doc['_id'] = str(doc['_id'])
            return doc

        return jsonify({
            "message": f"{len(inserted_ids)} documentos insertados",
            "inserted_ids": inserted_ids,
            "documentos": [limpiar_doc(doc) for doc in docs_insertados]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/diagnostico-filtros', methods=['GET'])
def diagnostico_filtros():
    stats = {
        "total_documentos": db.delitos.count_documents({}),
        "con_municipio_celaya": db.delitos.count_documents({
            "municipio": {"$regex": "^CELAYA$", "$options": "i"}
        }),
        "con_colonia_valida": db.delitos.count_documents({
            "colonia": {"$exists": True, "$ne": None, "$ne": ""}
        }),
        "con_coordenadas": db.delitos.count_documents({
            "ubicacion.coordinates": {"$exists": True}
        }),
        "cumplen_todos_filtros": db.delitos.count_documents({
            "municipio": {"$regex": "^CELAYA$", "$options": "i"},
            "colonia": {"$exists": True, "$ne": None, "$ne": ""},
            "ubicacion.coordinates": {"$exists": True}
        })
    }

    return jsonify(stats)

@app.route('/api/zonas', methods=['GET'])
def get_zonas():
    try:
        pipeline = [
            {
                "$match": {
                    "municipio": {"$exists": True},
                    "colonia": {"$exists": True}
                }
            },
            {
                "$group": {
                    "_id": "$colonia",
                    "total": {"$sum": 1},
                    "coordenadas": {
                        "$first": {
                            "$cond": [
                                {"$ifNull": ["$ubicacion.coordinates", False]},
                                "$ubicacion",
                                None
                            ]
                        }
                    },
                    "tipos_delitos": {"$addToSet": "$delito"},
                    "ultimo_incidente": {"$max": "$fecha_completa"}
                }
            },
            {
                "$project": {
                    "colonia": "$_id",
                    "total": 1,
                    "coordenadas": 1,
                    "variedad_delitos": {"$size": "$tipos_delitos"},
                    "tipos_delitos": {"$slice": ["$tipos_delitos", 5]},
                    "ultimo_incidente": 1,
                    "nivel_peligro": {
                        "$switch": {
                            "branches": [
                                {"case": {"$gte": ["$total", 15]}, "then": "Alto"},
                                {"case": {"$gte": ["$total", 8]}, "then": "Medio"},
                                {"case": {"$lt": ["$total", 8]}, "then": "Bajo"}
                            ]
                        }
                    }
                }
            },
            {"$sort": {"total": -1}},
            {"$match": {"total": {"$gt": 0}}}
        ]

        resultados = list(db.delitos.aggregate(pipeline))

        return jsonify({
            "status": "success",
            "count": len(resultados),
            "data": resultados
        })

    except Exception as e:
        app.logger.error(f"Error en /api/zonas: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Error al procesar la solicitud",
            "details": str(e)
        }), 500


if __name__ == '__main__':
    app.run(debug=True)