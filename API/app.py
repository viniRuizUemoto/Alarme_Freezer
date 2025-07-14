from flask import Flask, request, redirect, jsonify, session, render_template, url_for, send_file
from flask_session import Session
import time
import requests
from threading import Thread, Lock
from queue import PriorityQueue
from datetime import datetime,timedelta, date
import os
from time import perf_counter as tic
from dotenv import find_dotenv, load_dotenv
from flask_sqlalchemy import SQLAlchemy
import numpy as np
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit
import pandas as pd


lock = Lock()

db = SQLAlchemy()

# Verifica se o freezer enviou uma request nos ultimos 61 segundos
# caso nao tenha mandado o Freezer é definido como com problema de
# comunicaçao.
def CheckReceive():
    global freezer_enable
    global last_request
    with app.app_context():
        list_freezers = db.session.query(Freezers).all()
        
        for i in list_freezers:
            if (time.perf_counter() - i.last_request > 601) and i.freezer_enable==1:
                requests.post("https://ntfy.sh/teste_freezer_fajdante",
                    data=f"Freezer {i.id} fora da Rede".encode(encoding='utf-8'),
                    verify=False)
                i.freezer_enable = 0
                db.session.commit()
                i.status = 0
                db.session.commit()
                evento = Evento(freezer_id=i.id,tipo='Falha de comunicação',data_hora=datetime.now())
                db.session.add(evento)
                db.session.commit()

jobs = PriorityQueue()

# Multithreat
class Queue(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.start()
    def run(self):
        while True:
            _, data = jobs.get()
            CheckReceive()

class backGroundProcess(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.start()
    def run(self):
        while True:
            time.sleep(2)
            jobs.put((0,"|"))

class flaskProcess(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.start()
    def run(self):
        jobs.put((1,"@"))


## API para receber requests do ESP32
app = Flask(__name__)
socketio = SocketIO(app,cors_allowed_origins="*")

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

app.secret_key = os.environ.get('SECRET_KEY')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
login_manager = LoginManager(app)
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(hours=8)


@login_manager.user_loader
def get_user(user_id):
    return Users.query.get(user_id)

## Modelos do Banco de Dados
class Evento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    freezer_id = db.Column(db.Integer)
    tipo = db.Column(db.String(50))
    data_hora = db.Column(db.DateTime)


class Registro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    freezer_id = db.Column(db.Integer)
    temperatura = db.Column(db.Float)
    data_hora = db.Column(db.DateTime)

class Freezers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Integer)
    freezer_enable = db.Column(db.Integer)
    temperature_inrange = db.Column(db.Integer)
    temperatura_definida = db.Column(db.Integer)
    last_request = db.Column(db.Float)
    modelo = db.Column(db.String(225))

class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(225))
    password = db.Column(db.String(128))
    def __init__(self, username, password):
        self.username = username
        self.password = generate_password_hash(password)

    def verify_password(self, pwd):
        return check_password_hash(self.password,pwd)
    
    def __repr__(self):
        return'<Nome %r>' % self.username

@app.route("/login", methods=['POST','GET'])
def login():
     if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Users.query.filter_by(username=username).first()
        if user and user.verify_password(password):
            login_user(user)
            return redirect(url_for('home'))
     return render_template('login.html')

@app.route("/logout", methods=['POST','GET'])
def logout():
     if request.method == 'POST':
        logout_user(current_user)
        return redirect(url_for('login'))
     

@app.route("/api/register/<int:id>", methods=['POST'])
def register_temp(id):
    data = request.get_json()
    print(data)
    registro = Registro(freezer_id = id, temperatura = data['temperatura'], data_hora = datetime.now())
    db.session.add(registro)
    db.session.commit()
    return jsonify({
        'statusCode': 200,
        'message': 'Temperatura recebida'
    })

@app.route("/warning/<int:id>", methods=['POST', 'GET'])
def api(id):
    id = id + 1
    # Recebe o Json do ESP32
    callback = request.get_json()
    
    # Retoma Variáveis globais
    freezer = db.session.query(Freezers).get(id)
    # Caso o freezer estivesse com problema de comunicaçao antes
    # redefine ele como comunicaçao apta
    if freezer.freezer_enable == 0:
        requests.post("https://ntfy.sh/teste_freezer_fajdante",
            data=f"Freezer retomou comunicação com a Rede".encode(encoding='utf-8'),
            verify=False)
        with open('log.txt','a') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Retomada de Comunicação\n")
        evento = Evento(freezer_id=freezer.id,tipo='Comunicação Reestabelecida',data_hora=datetime.now())
        db.session.add(evento)
        freezer.freezer_enable = 1
        freezer.status = 1
        db.session.commit()
    # Reseta o instante da ultima request
    freezer.last_request = time.perf_counter()
    db.session.commit()
    # Caso o alarme seja acionado e a leitura anterior estivesse normal
    # é enviada uma notificaçao pelo ntfy e retorna um json informando
    # que a notificaçao foi enviada
    if callback['status'] != 200 and freezer.temperature_inrange == 1:
        evento = Evento(freezer_id=freezer.id,tipo='Fora da Temperatura',data_hora=datetime.now())
        db.session.add(evento)
        db.session.commit()
        r=requests.post("https://ntfy.sh/teste_freezer_fajdante",
            data=f"Temperatura do Freezer {id} fora do aceitável".encode(encoding='utf-8'),
            verify=False)
        freezer.temperature_inrange = 0
        freezer.status = -1
        db.session.commit()
        return jsonify({
            'statusCode': 201,
            'message': 'Mensagem de freezer fora da temperatura enviada'
        })
    
    # Caso a leitura anterior tivesse sido de erro, reseta o valor da variável
    # indicando temperatura dentro da normalidade
    if freezer.temperature_inrange==0 and callback['status'] == 200:
        evento = Evento(freezer_id=freezer.id,tipo='Retornou a Temperatura desejada',data_hora=datetime.now())
        db.session.add(evento)
        db.session.commit()
        freezer.status = 1
        freezer.temperature_inrange = 1
        db.session.commit()
        return jsonify({
            'statusCode': 200,
            'message': 'OK'
        })
    # Retorna Json indicando leitura normal e nenhuma notificaçao enviada
    return jsonify({
            'statusCode': 202,
            'message': 'Temperatura normal dentro do Aceitável'
        })


# DashBoard para monitoramento dos Freezers
@app.route("/", methods=['POST', 'GET'])
@login_required
def home():
    lista_freezers = db.session.query(Freezers).all()
    atualizado = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    warings = db.session.query(Evento).filter(Evento.data_hora > datetime(2020,1,1)).order_by(Evento.data_hora.desc()).all()
    if len(warings) > 10:
        warings = warings[:10]
    temperaturas = {}
    for freeze in lista_freezers:
        registro = db.session.query(Registro).filter(Registro.freezer_id==freeze.id).order_by(Registro.data_hora.desc()).first()
        if registro:
            temperaturas[freeze.modelo] = registro.temperatura
        else:
            temperaturas[freeze.modelo] = freeze.temperatura_definida
    return render_template('dash.html', atualizado=atualizado,
                            warings=warings, lista_freezers=lista_freezers, temp = temperaturas)

# Cadastro de Freezer
@app.route("/cadastro", methods=['POST', 'GET'])
@login_required
def cadastro():
    if request.method == "POST":
        modelo = request.form.get('Modelo')
        marca = request.form.get('Marca')
        temperatura = request.form.get('Temperatura')
        nome = modelo.upper()+'-'+marca.upper()
        newfreezer = Freezers(status=1,freezer_enable=1,temperature_inrange=1,last_request=tic(),modelo=nome)
        db.session.add(newfreezer)
        db.session.commit()
    return render_template("cadastro.html")

# Página Individual de cada Freezer
@app.route("/info/<int:id>")
@login_required
def info(id):
    data_com = {'noCom':0,'tempofalha': []}
    data_temperatura = {'qtde':0, 'tempo':[]}
    registros = db.session.query(Evento).filter_by(freezer_id=id).order_by(Evento.data_hora).all()
    for registro in registros:
        start_com = registro.data_hora
        if registro.tipo == 'Falha de comunicação':
            data_com['noCom'] += 1
        elif registro.tipo == 'Comunicação Reestabelecida':
            data_com['tempofalha'].append((registro.data_hora -  start_com).total_seconds())
        elif registro.tipo == "Fora da Temperatura":
            start_temp = registro.data_hora
            data_temperatura['qtde'] += 1
        else:
            data_temperatura['tempo'].append((registro.data_hora - start_temp).total_seconds())
        data_com['tempoMed'] = np.median(data_com['tempofalha'])
        data_temperatura['tempoMed'] = np.median(data_temperatura['tempo'])

    return render_template('info.html', registros = registros, data_temperatura=data_temperatura, data_com=data_com)

@app.route("/report", methods=['POST', 'GET'])
@login_required
def report():
    if request.method == "POST":
        excel_file = f"{datetime.now().strftime('%Y_%m_%d')}_{current_user.id}.xlsx"
        excel_path = os.path.join(os.getcwd(),'static','files',excel_file)
        start = request.form.get('start')
        end = request.form.get('end')
        writer = pd.ExcelWriter(excel_path)
        for k in request.form.getlist('freezers'):
            freezer = db.session.query(Freezers).get(int(k))
            df = []
            
            registros = db.session.query(Registro)\
                .filter(Registro.freezer_id == freezer.id)\
                .filter(Registro.data_hora <= end)\
                .filter(Registro.data_hora >= start).all()
            
            for reg in registros:
                df.append({'DataHora':reg.data_hora.strftime("%d/%m/%Y %H:%M:%S"), 'Temperatura [°C]':reg.temperatura})
            print(pd.DataFrame(df).head())
            pd.DataFrame(df).to_excel(writer,sheet_name=freezer.modelo,index=False)
        writer.close()
        return send_file(excel_path)

    list_freezers = db.session.query(Freezers).all()
    lista_available = []
    for k in list_freezers:
        registrosOfFreezer = db.session.query(Registro).filter(Registro.freezer_id==k.id).all()
        if registrosOfFreezer and len(registrosOfFreezer) > 0:
            lista_available.append(k)
    return render_template('GerarRelatorio.html', lista_freezers = list_freezers)

@socketio.on('update')
def update_data():
    lista_freezers = db.session.query(Freezers).all()
    freezers = []

    for freeze in lista_freezers:
        last_registro = db.session.query(Registro).filter(Registro.freezer_id==freeze.id).order_by(Registro.data_hora.desc()).first()
        try:
            freezers.append({"ID": freeze.id, "Modelo":freeze.modelo, "Status":freeze.status, "Temperatura":last_registro.temperatura, "data_hora": last_registro.data_hora.strftime("%d/%m/%Y %H:%M:%S")})
        except:
            freezers.append({"ID": freeze.id, "Modelo":freeze.modelo, "Status":freeze.status, "Temperatura":0, "data_hora": ''})
    atualizado = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    warings = db.session.query(Evento).filter(Evento.data_hora > datetime(2020,1,1)).order_by(Evento.data_hora.desc()).all()
    if len(warings) > 10:
        warings = warings[:10]
    warnings = []
    for i in warings:
        warnings.append({"freezer": db.session.query(Freezers).get(i.freezer_id).modelo, "tipo":i.tipo,"data": i.data_hora.strftime("%d/%m/%Y %H:%M:%S")})
    emit("recebi", {'data':atualizado, 'freezers':freezers, 'warnings': warnings}, namespace='/',broadcast=True)

if __name__ == '__main__':
    backGroundProcess()
    Queue()
    socketio.run(app, host='0.0.0.0', port=8800, allow_unsafe_werkzeug=True)
