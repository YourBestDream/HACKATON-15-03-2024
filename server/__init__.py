import os

from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = f'{os.environ.get("SECRET_KEY")}'
    CORS(app)

    from .views import views
    from .requests import requests

    app.register_blueprint(views, url_prefix = '/')
    app.register_blueprint(requests, url_prefix = '/')

    return app