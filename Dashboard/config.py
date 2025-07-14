import os
import dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
dotenv.load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URI")