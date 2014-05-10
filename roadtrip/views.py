from flask import render_template, redirect, url_for, flash, request, session, g
from flask.ext.security import login_required, current_user

from roadtrip import app, db, user_datastore
from roadtrip.models import User

@app.route('/')
@app.route('/index')
@login_required
def index():
	return render_template("index.html", user=current_user, title="Home")

@app.route('/signup')
def signup():
	""" Create a new account. """
	pass

@app.route('/newtrip')
def new_trip():
	""" Create a new road trip."""
	pass

@app.route('/trip/<trip_name>')
def trip(trip_name):
	""" Loads a particular trip """
	pass

@app.route('/edit/<trip_name>')
def edit_trip(trip_name):
	""" Edit a given road trip. """
	pass

def upload_image(trip, day=None):
	""" Uploads image(s) to a roadtrip. A day might be specified, but if not the
	photos are added to an unused bin.
	"""
	pass

def delete_image(image):
	""" Delete a particular image"""
	pass