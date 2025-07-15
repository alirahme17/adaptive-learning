# database.py

from flask import Flask
from flask_mysqldb import MySQL
from config import Config

mysql = MySQL()

def init_db(app):
    app.config.from_object(Config)
    mysql.init_app(app)

def get_db():
    return mysql