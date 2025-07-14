from applicationDev import app, db, Freezers,Registro,Evento, Users
from argparse import ArgumentParser
from datetime import datetime
from time import perf_counter as tic

with app.app_context():
    Eventos = db.session.query(Evento).all()
    for k in Eventos:
        print(k.tipo)
    freezers = db.session.query(Freezers).all()
    for k in freezers:
        print(k.id)
        print(k.modelo)
    users = db.session.query(Users).all()
    for j in users:
        print(j)
