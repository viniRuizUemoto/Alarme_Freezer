from applicationDev import app, db, Freezers,Registro,Evento
from argparse import ArgumentParser
from datetime import datetime
from time import perf_counter as tic


def delete_all():
    with app.app_context():
        freezers = db.session.query(Freezers).all()
        for i in freezers:
            db.session.delete(i)
        eventos =  db.session.query(Evento).all()
        for i in eventos:
            db.session.delete(i)
        registros =  db.session.query(Registro).all()
        for i in registros:
            db.session.delete(i)
        db.session.commit()
    return "OK"

def delete_registros():
    with app.app_context():
        eventos =  db.session.query(Evento).all()
        for i in eventos:
            db.session.delete(i)
        registros =  db.session.query(Registro).all()
        for i in registros:
            db.session.delete(i)
        db.session.commit()
    return "OK"

def delete_fromdate(date):
    with app.app_context():
        eventos =  db.session.query(Evento).filter_by(data_hora<=date).all()
        for i in eventos:
            db.session.delete(i)
        registros =  db.session.query(Registro).all()
        for i in registros:
            db.session.delete(i)
        db.session.commit()
    return "OK"

def main():
    parser = ArgumentParser()
    parser.add_argument("type", help="1 = Deletar tudo em todas tabelas; 2 = Deletar registros de temperatura e Eventos/Alarmes")
    parser.add_argument("date")
    args = parser.parse_args()
    if args.type == '1':
        delete_all()
    elif args.type == '2':
        delete_registros()
    elif args.type == '0':
        with app.app_context():
            db.drop_all()
    elif args.type == '3':
        delete_fromdate(datetime.strptime(args.date, '%Y-%m-%d'))
    else:
        raise Exception("Comando Inválido (valores aceitos 1 e 2)")

if __name__ == "__main__":
    main()
