from app import app, db, Freezers,Registro,Evento,Users
from argparse import ArgumentParser
from datetime import datetime
from time import perf_counter as tic

with app.app_context():
    db.create_all()
    
