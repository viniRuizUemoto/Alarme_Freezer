from flask import Flask
from config import Config
from api.routes import api_bp
from extensions import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.register_blueprint(api_bp, url_prefix='/api')

    db.init_app(app)

    return app
