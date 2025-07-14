from extensions import db

class Registro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    freezer_id = db.Column(db.Integer)
    temperatura = db.Column(db.Float)
    data_hora = db.Column(db.DateTime)