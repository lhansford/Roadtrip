from flask import render_template

from roadtrip import app

@app.route('/')
def index():
    return render_template("index.html")

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

