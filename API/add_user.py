from applicationDev import app, db, Freezers, Users
from argparse import ArgumentParser
from datetime import datetime
from time import perf_counter as tic

with app.app_context():
    parser = ArgumentParser()
    parser.add_argument("nome")
    parser.add_argument("senha")
    args = parser.parse_args()
    user = Users(username=args.nome, password=args.senha)
    db.session.add(user)
    db.session.commit()
