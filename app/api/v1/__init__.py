# app/api/v1/__init__.py
from flask import Blueprint

bp = Blueprint('api', __name__)

from app.api.v1 import routes