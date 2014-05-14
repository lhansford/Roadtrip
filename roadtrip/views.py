from datetime import datetime, timedelta
import math

from flask import render_template, redirect, url_for, flash, request, session, g, jsonify
from flask.ext.security import login_required, current_user

import requests
from sqlalchemy import desc

from roadtrip import app, db, user_datastore
from roadtrip.models import User, Trip, Day, Location
from roadtrip.forms import TripForm, DayForm, DestinationForm

@app.route('/')
@app.route('/index')
@login_required
def index():
	trips = Trip.query.filter_by(user_id=current_user.id).all()
	return render_template("index.html",
	 user=current_user,
	 trips=trips,
	 title="Home")

@app.route('/signup')
def signup():
	""" Create a new account. """
	pass

@app.route('/newtrip', methods = ['GET', 'POST'])
def new_trip():
	""" Create a new road trip."""
	form = TripForm(request.form)
	if form.validate_on_submit():
		trip = Trip(
			name = form.name.data,
			user = current_user
		)
		db.session.add(trip)
		day = Day(
			date = datetime.strptime(form.start_date.data, '%a %b %d %Y'),
			trip = trip
		)
		latlng = get_location(form.start_location.data.split())
		location = Location(
			name = form.start_location.data,
			latitude = float(latlng[0]),
			longitude = float(latlng[1]),
			order = 1,
			day = day
		)
		db.session.add(trip)
		db.session.add(day)
		db.session.add(location)
		db.session.commit()
		flash('Your trip has been created.')
		return redirect(url_for('index'))
	return render_template("new_trip.html", form = form)

@app.route('/trip/<trip_name>')
def trip(trip_name):
	""" Loads a particular trip """
	pass

@app.route('/trip/<int:trip_id>/<int:day_num>')
def day(trip_id, day_num):
	""" Loads a particular day of a trip """
	trip = Trip.query.get(trip_id)
	days = Day.query.filter_by(trip=trip).order_by(Day.date).limit(day_num).all()
	if len(days) != day_num:
		return "ERROR"
	day = days[-1]
	locations = []
	for l in Location.query.filter_by(day=day).all():
		d = {}
		d['name'] = l.name
		d['latitude'] = l.latitude
		d['longitude'] = l.longitude
		locations.append(d)
	route = None
	if len(locations) > 1:
		route = get_route(locations)
	return render_template("day.html", trip=trip, day=day, day_num=day_num, locations=locations, route=route)

@app.route('/trip/<int:trip_id>/edit')
def edit_trip(trip_id):
	""" Edit a given road trip. """
	trip = Trip.query.get(trip_id)
	days = Day.query.filter_by(trip=trip).order_by(Day.date).all()
	trip_data = []
	num = 1
	for day in days:
		d = {}
		d['date'] = day.date
		d['num'] = num
		d['locations'] = Location.query.filter_by(day=day).all()
		trip_data.append(d)
		num += 1
	return render_template("edit_trip.html", trip=trip, days=trip_data)

@app.route('/trip/<int:trip_id>/<int:day_num>/edit')
def edit_day(trip_id, day_num):
	""" Edit a given road trip. """
	trip = Trip.query.get(trip_id)
	days = Day.query.filter_by(trip=trip).order_by(Day.date).limit(day_num).all()
	if len(days) != day_num:
		return "ERROR"
	day = days[-1]
	locations = Location.query.filter_by(day=day).all()
	return render_template("edit_day.html", trip=trip, day=day, day_num=day_num, locations=locations)

@app.route('/trip/<int:trip_id>/_add_day')
def _add_day(trip_id):
	""" Add a day to a trip and return it as JSON """
	trip = Trip.query.get(trip_id)
	last_day = Day.query.filter_by(trip=trip).order_by(desc(Day.date)).first()
	last_location = Location.query.filter_by(day=last_day).order_by(desc(Location.order)).first()
	new_day = Day(
		date = last_day.date + timedelta(days=1),
		trip = trip
	)
	new_location = Location(
		name = last_location.name,
		latitude = last_location.latitude,
		longitude = last_location.longitude,
		order = 1,
		day = new_day
	)
	db.session.add(new_day)
	db.session.add(new_location)
	db.session.commit()
	# return jsonify(new_day = new_day, new_location = new_location)
	return jsonify({"TEST":1})

@app.route('/trip/<int:trip_id>/<int:day_num>/_add/<location_query>')
def _add_location(trip_id, day_num, location_query):
	""" Add a location to a day and return it as JSON """
	location = location_query.split('+')
	trip = Trip.query.get(trip_id)
	days = Day.query.filter_by(trip=trip).order_by(Day.date).limit(day_num).all()
	if len(days) != day_num:
		return "ERROR"
	day = days[-1]
	order = Location.query.filter_by(day=day).count() + 1
	latlng = get_location(location)
	new_location = Location(
		name = ' '.join(location),
		latitude = latlng[0],
		longitude = latlng[1],
		order = 1,
		day = day
	)
	db.session.add(new_location)
	db.session.commit()
	# return jsonify(new_day = new_day, new_location = new_location)
	return jsonify({"TEST":1})

def get_location(query):
	""" Returns the latitude and longitude of a location. Query is a comma 
	seperated list of keywords. NEEDS IMPROVEMENT FOR 
	MULTIPLE OPTIONS OR NO RESULT. """
	url = "http://nominatim.openstreetmap.org/search?q=" + '+'.join(query) + '&format=json&limit=1' #Currently only get one
	r = requests.get(url)
	data = r.json()[0] #Get first element of list, should only be one atm.
	return (data['lat'],data['lon'])

def upload_image(trip, day=None):
	""" Uploads image(s) to a roadtrip. A day might be specified, but if not the
	photos are added to an unused bin.
	"""
	pass

def delete_image(image):
	""" Delete a particular image"""
	pass

def get_route(locations):
	""" Returns a route between the given locations. Locations is a list of 
	dicts where each dict contains a name, latitude, and longitude.
	"""
	server = "http://router.project-osrm.org/"
	query = 'viaroute?loc='
	for location in locations:
		query += str(location['latitude'])
		query += ','
		query += str(location['longitude'])
		query += '&loc='
	query = query [:-5] #Remove last '&loc='
	r = requests.get(server + query)
	return decode_polyline(r.json()['route_geometry'])

def decode_polyline(encoded_string):
	'''Decodes a polyline that has been encoded using Google's algorithm
	http://code.google.com/apis/maps/documentation/polylinealgorithm.html
	
	This is a generic method that returns a list of (latitude, longitude) 
	tuples.
	
	:param point_str: Encoded polyline string.
	:type point_str: string
	:returns: List of 2-tuples where each tuple is (latitude, longitude)
	:rtype: list
	
	Borrowed from http://www.mail-archive.com/osrm-talk@openstreetmap.org/msg00324.html
	'''
	precision = 6
	decode_precision = math.pow(10, precision * -1)
	encoded_length = len(encoded_string)
	index = 0
	lat = 0
	lon = 0
	output_array = []

	while index < encoded_length:
		b = 0
		shift = 0
		result = 0

		while True:
			b = ord(encoded_string[index]) - 63
			index += 1
			result |= (b & 0x1f) << shift
			shift += 5
			if b < 0x20:
				break
		if result & 1:
			dlat = ~(result >> 1)
		else:
			dlat = result >> 1
		lat += dlat

		shift = 0
		result = 0

		while True:
			b = ord(encoded_string[index]) - 63
			index += 1
			result |= (b & 0x1f) << shift
			shift += 5
			if b < 0x20:
				break
		if result & 1:
			dlon = ~(result >> 1)
		else:
			dlon = result >> 1
		lon += dlon
		output_array.append([lat*decode_precision, lon*decode_precision])
	return output_array

