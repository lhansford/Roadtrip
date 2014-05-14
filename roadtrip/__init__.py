import os

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.migrate import Migrate
from flask.ext.bcrypt import Bcrypt
from flask.ext.security import Security, SQLAlchemyUserDatastore

from config import basedir

app = Flask(__name__)
app.config.from_object('config')
app.config['SECURITY_REGISTERABLE'] = True
#TODO - make proper confirmation email
app.config['SECURITY_SEND_REGISTER_EMAIL'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
# bcrypt = Bcrypt(app)
app.config['SECURITY_PASSWORD_HASH'] = 'bcrypt'
app.config['SECURITY_PASSWORD_SALT'] = 'bcrypt'

from roadtrip.models import User, Role
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

from roadtrip import views, models