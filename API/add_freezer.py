from applicationDev import app, db, Freezers
from argparse import ArgumentParser
from datetime import datetime
from time import perf_counter as tic

with app.app_context():
    parser = ArgumentParser()
    parser.add_argument("nome")
    args = parser.parse_args()
    newfreezer = Freezers(status=1,freezer_enable=1,temperature_inrange=1,last_request=tic(),modelo=args.nome)
    db.session.add(newfreezer)
    db.session.commit()
