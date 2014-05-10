from roadtrip import db
from flask.ext.security import UserMixin, RoleMixin

# Define models
roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
	id = db.Column(db.Integer(), primary_key=True)
	name = db.Column(db.String(80), unique=True)
	description = db.Column(db.String(255))

class User(db.Model, UserMixin):
	id = db.Column(db.Integer, primary_key=True)
	email = db.Column(db.String(255), unique=True)
	password = db.Column(db.String(255))
	active = db.Column(db.Boolean())
	confirmed_at = db.Column(db.DateTime())
	roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))

class Trip(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(255))
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	user = db.relationship('User', backref=db.backref('users', lazy='dynamic'))

class Day(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.Date)
	trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'))
	trip = db.relationship('Trip', backref=db.backref('days', lazy='dynamic'))

class Location(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(255))
	latitude = db.Column(db.Float)
	longitude = db.Column(db.Float)
	order = db.Column(db.Integer) 
	day_id = db.Column(db.Integer, db.ForeignKey('day.id'))
	day = db.relationship('Day', backref=db.backref('locations', lazy='dynamic'))