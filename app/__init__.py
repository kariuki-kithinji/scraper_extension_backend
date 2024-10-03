# app/__init__.py
from flask import Flask
from flask_cors import CORS
from redis import Redis
from rq import Queue
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

from app.models import db
from app.tasks import celery
from app.utils import cache , limiter
from app.api.v1 import bp as api_v1_bp

# Load environment variables
load_dotenv()


def create_app():
    app = Flask(__name__)

    # Configurations
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['CACHE_TYPE'] = 'redis'
    app.config['CACHE_REDIS_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300
    app.config['CELERY_BROKER_URL'] = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    app.config['result_backend'] = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

    # Initialize extensions with app
    db.init_app(app)
    cache.init_app(app)
    CORS(app)
    limiter.init_app(app)
    celery.conf.update(app.config)
    celery.autodiscover_tasks(['app','app.tasks','app.api.v1.routes'],force=True)
    
    # Create the database tables if not exists
    with app.app_context():
        db.create_all()

    # Set up logging
    if not app.debug:
        file_handler = RotatingFileHandler('app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application startup')

    # Initialize Redis Queue
    app.redis = Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/3'))
    app.task_queue = Queue(connection=app.redis)

    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')

    return app