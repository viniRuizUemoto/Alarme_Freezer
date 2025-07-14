from flask import jsonify, Blueprint, request
from extensions import db
from models.registros import Registro
from datetime import datetime

api_bp = Blueprint('api_bp', __name__, template_folder = 'templates', static_folder = 'static', static_url_path='assets')

@api_bp.route('/registro', methods=['GET','POST'])
def register_temp ():
    if request.method=='GET':
        registros = Registro.query.all()
        response = {'status': 200, 'data': {'registros': []}}
        for r in registros:
            aux = {'id': r.id,'freezer_id':r.freezer_id,'temperatura':f'{r.temperatura}°C','data_hora':r.data_hora.strftime("%d/%m/%Y %H:%M:%S")}
            response['data']['registros'].append(aux)
        
    else:
        request_data = request.get_json()
        try:
            registro_novo = Registro(freezer_id = request_data["freezer_id"], temperatura = request_data['temperatura'], data_hora=datetime.now())
            db.session.add(registro_novo)
            db.session.commit()
            response = {"status": 200, 'message': 'OK'}
        except KeyError:
            response = {"status": 500, 'message': 'Data in wrong format'}
    return jsonify(response)