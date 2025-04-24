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

@app.route('/diagnostico/percentiles')
def diagnostico_percentiles():
    try:
        pipeline = [
            {"$match": {
                "municipio": {"$regex": "^CELAYA$", "$options": "i"},
                "colonia": {"$exists": True, "$ne": None, "$ne": ""}
            }},
            {"$group": {
                "_id": "$colonia",
                "total": {"$sum": 1}
            }},
            {"$sort": {"total": 1}}
        ]
        datos = list(db.delitos.aggregate(pipeline))

        # Extraemos solo los valores totales
        totales = [d["total"] for d in datos]

        if not totales:
            return jsonify({"error": "No se encontraron datos"}), 404

        # Cálculo de percentiles
        import numpy as np
        p25 = int(np.percentile(totales, 25))
        p50 = int(np.percentile(totales, 50))
        p75 = int(np.percentile(totales, 75))

        return jsonify({
            "total_colonias": len(totales),
            "percentil_25": p25,
            "percentil_50": p50,
            "percentil_75": p75,
            "maximo": max(totales),
            "minimo": min(totales)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/colonias', methods=['GET'])
def get_colonias():
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
                                {"case": {"$gte": ["$total", 100]}, "then": "Alto"},
                                {"case": {"$gte": ["$total", 50]}, "then": "Medio"},
                                {"case": {"$lt": ["$total", 49]}, "then": "Bajo"}
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
        app.logger.error(f"Error en /api/colonias: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Error al procesar la solicitud",
            "details": str(e)
        }), 500


@app.route('/api/calles', methods=['GET'])
def get_calles():
    try:
        # Pipeline base
        match_stage = {
            "municipio": {"$regex": "^CELAYA$", "$options": "i"},
            "calle": {"$exists": True, "$ne": None, "$ne": "", "$ne": "NO CATALOGADO"}
        }

        pipeline = [
            {"$match": match_stage},
            {
                "$group": {
                    "_id": {
                        "calle": "$calle",
                        "colonia": "$colonia"
                    },
                    "total": {"$sum": 1},
                    "coordenadas": {"$first": "$ubicacion"},
                    "tipos_delitos": {"$push": "$delito"}
                }
            },
            {
                "$project": {
                    "calle": "$_id.calle",
                    "colonia": "$_id.colonia",
                    "total": 1,
                    "coordenadas": 1,
                    "variedad_delitos": {"$size": "$tipos_delitos"},
                    "nivel_peligro": {
                        "$switch": {
                            "branches": [
                                {"case": {"$gte": ["$total", 10]}, "then": "Alto"},
                                {"case": {"$gte": ["$total", 5]}, "then": "Medio"},
                                {"case": {"$lt": ["$total", 5]}, "then": "Bajo"}
                            ]
                        }
                    }
                }
            },
            {"$sort": {"total": -1}}
        ]


        resultados = list(db.delitos.aggregate(pipeline))

        return jsonify({
            "status": "success",
            "count": len(resultados),
            "data": resultados
        })

    except Exception as e:
        app.logger.error(f"Error en /api/calles: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Error al procesar la solicitud"
        }), 500

if __name__ == '__main__':
    app.run(debug=True)