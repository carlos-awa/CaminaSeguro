from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()  # Carga variables de entorno

app = Flask(__name__)

# Conexión usando la variable de entorno
client = MongoClient(os.getenv("MONGODB_URI"))
db = client.get_database()


@app.route('/')
def home():
    return render_template('index.html')

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

        resultados = list(db.delitos_prueba.aggregate(pipeline))

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
                                {"case": {"$gte": ["$total", 100]}, "then": "Alto"},
                                {"case": {"$gte": ["$total", 50]}, "then": "Medio"},
                                {"case": {"$lt": ["$total", 50]}, "then": "Bajo"}
                            ]
                        }
                    }
                }
            },
            {"$sort": {"total": -1}}
        ]


        resultados = list(db.delitos_prueba.aggregate(pipeline))

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


@app.route('/api/delitos/search', methods=['GET'])
def search_delitos():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({"data": []})

    # Obtener sugerencias de delitos existentes
    delitos = db.delitos_prueba.distinct("delito", {"delito": {"$regex": query, "$options": "i"}})
    # Convertir a un formato que el autocompletado JS espera
    suggestions = [{"delito": d} for d in delitos]
    return jsonify({"data": suggestions})

@app.route('/api/calles/search', methods=['GET'])
def search_calles():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({"data": []})

    calles = db.delitos_prueba.distinct("calle", {
        "municipio": {"$regex": "^CELAYA$", "$options": "i"},
        "calle": {"$regex": query, "$options": "i", "$ne": None, "$ne": "", "$ne": "NO CATALOGADO"}
    })
    suggestions = [{"nombre": c} for c in calles]
    return jsonify({"data": suggestions})

@app.route('/api/colonias/search', methods=['GET'])
def search_colonias():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({"data": []})

    colonias = db.delitos_prueba.distinct("colonia", {
        "municipio": {"$regex": "^CELAYA$", "$options": "i"},
        "colonia": {"$regex": query, "$options": "i", "$ne": None, "$ne": ""}
    })
    suggestions = [{"colonia": c} for c in colonias]
    return jsonify({"data": suggestions})

@app.route('/api/delitos', methods=['POST'])
def add_delito():
    try:
        data = request.get_json()
        
        # Validar datos mínimos
        required_fields = ['delito', 'calle', 'colonia', 'fecha', 'hora', 'lat', 'lon', 'municipio']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    "status": "error", 
                    "message": f"Campo '{field}' es requerido."
                }), 400

        # Crear el documento para insertar
        delito_doc = {
            "delito": data['delito'].strip().upper(),
            "municipio": data['municipio'].strip().upper(),
            "colonia": data['colonia'].strip(),
            "calle": data['calle'].strip(),
            "forma_accion": data.get('forma_accion', 'SIN ESPECIFICAR').strip().upper(), # Usa get para un valor predeterminado
            "ubicacion": {
                "type": "Point",
                "coordinates": [float(data['lon']), float(data['lat'])]
            },
            # Combinar fecha y hora para fecha_completa y extraer anio, mes, dia
            "fecha_completa": datetime.strptime(f"{data['fecha']} {data['hora']}", "%Y-%m-%d %H:%M"),
        }
        
        # Opcional: Extraer año, mes y día para mantener el formato de tus datos existentes
        delito_doc["anio"] = delito_doc["fecha_completa"].year
        delito_doc["mes_nombre"] = delito_doc["fecha_completa"].strftime("%B").upper() # Nombre del mes
        delito_doc["dia"] = delito_doc["fecha_completa"].day

        # Insertar en la colección
        result = db.delitos_prueba.insert_one(delito_doc)

        return jsonify({
            "status": "success",
            "message": "Delito registrado exitosamente",
            "id": str(result.inserted_id)
        }), 201

    except ValueError as ve:
        app.logger.error(f"Error de validación al agregar delito: {str(ve)}")
        return jsonify({
            "status": "error",
            "message": "Datos de entrada inválidos",
            "details": str(ve)
        }), 400
    except Exception as e:
        app.logger.error(f"Error al agregar delito: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Error interno del servidor al registrar el delito",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5050)