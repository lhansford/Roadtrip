from datetime import datetime, timedelta
import math
import json

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

@app.route('/newtrip', methods = ['GET', 'POST'])
@login_required
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
	locations = [{'latitude':l.latitude, 'longitude':l.longitude} for l in Location.query.filter_by(day=day).order_by(Location.order).all()]
	route = None
	if len(locations) > 1:
		route = get_route(locations)
	return render_template("day.html", trip=trip, day=day, day_num=day_num, locations=locations, route=route)

@app.route('/trip/<int:trip_id>/edit')
@login_required
def edit_trip(trip_id):
	""" Edit a given road trip. """

	trip = Trip.query.get(trip_id)
	#Redirect if not the current user
	if current_user != trip.user:
		return redirect('index')
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
@login_required
def edit_day(trip_id, day_num):
	""" Edit a given road trip. """
	trip = Trip.query.get(trip_id)
	#Redirect if not the current user
	if current_user != trip.user:
		return redirect('index')
	days = Day.query.filter_by(trip=trip).order_by(Day.date).limit(day_num).all()
	if len(days) != day_num:
		return "ERROR"
	day = days[-1]
	locations = Location.query.filter_by(day=day).order_by(Location.order).all()
	return render_template("edit_day.html", trip=trip, day=day, day_num=day_num, locations=locations)

@app.route('/trip/<int:trip_id>/_add_day')
@login_required
def _add_day(trip_id):
	""" Add a day to a trip and return it as JSON """
	trip = Trip.query.get(trip_id)
	#Redirect if not the current user
	if current_user != trip.user:
		return redirect('index')
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
	new_data = {
		"day": Day.query.count(),
		"date": new_day.date,
		"location": new_location.name
	} 
	return jsonify(new_data)

@app.route('/trip/<int:trip_id>/<int:day_num>/_add/<location_query>')
@login_required
def _add_location(trip_id, day_num, location_query):
	""" Add a location to a day and return it as JSON """
	location = location_query.split('+')
	trip = Trip.query.get(trip_id)
	#Redirect if not the current user
	if current_user != trip.user:
		return redirect('index')
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
		order = order,
		day = day
	)
	db.session.add(new_location)
	db.session.commit()
	# return jsonify(new_day = new_day, new_location = new_location)
	return jsonify({"TEST":1})

@app.route('/_remove_day/<int:trip_id>')
@login_required
def _remove_day(trip_id):
	""" Removes the last day of a trip. """
	trip = Trip.query.get(trip_id)
	#Redirect if not the current user
	if current_user != trip.user:
		return redirect('index')
	day = Day.query.filter_by(trip=trip).order_by(desc(Day.date)).first()
	db.session.delete(day)
	db.session.commit()
	return jsonify({})

@app.route('/_remove_location/<int:location_id>')
@login_required
def _remove_location(location_id):
	""" Removes a given location from the database. """
	location = Location.query.get(location_id)
	#Redirect if not the current user
	if current_user != location.day.trip.user:
		return redirect('index')
	db.session.delete(location)
	db.session.commit()
	return jsonify({})

#APP ROUTE
@app.route('/reorder_locations', methods=['POST'])
@login_required
def reorder_locations():
	"""Takes a JSON list and sets the order for the locations in the list to the
	same order as the list.
	"""
	## Convert JSON to list
	order = 1
	locations = request.get_json()
	for l_id in locations:
		location = Location.query.get(int(l_id))
		location.order = order
		db.session.commit()
		order += 1
	return "Okay"

def get_location(query):
	""" Returns a tuple containing the latitude and longitude of the result. 
	Query is a comma seperated list of keywords. NEEDS IMPROVEMENT FOR 
	MULTIPLE OPTIONS OR NO RESULT.
	"""
	query = '+'.join(query) + '&format=json&limit=1' #Currently only get one
	url = "http://nominatim.openstreetmap.org/search?q=" + query	 
	r = requests.get(url)
	data = r.json()[0] #Get first element of list, should only be one atm.
	return (data['lat'],data['lon'])

def get_route(locations):
	""" Returns a list of latlng tuples representing a journey. Locations is a 
	list of dicts where each dict contains a latitude and longitude.
	"""
	url = "http://router.project-osrm.org/viaroute?loc="
	for location in locations:
		url += str(location['latitude'])
		url += ','
		url += str(location['longitude'])
		url += '&loc='
	r = requests.get(url[:-5]) #Remove last '&loc='
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


def upload_image(trip, day=None):
	""" Uploads image(s) to a roadtrip. A day might be specified, but if not the
	photos are added to an unused bin.
	"""
	pass

def delete_image(image):
	""" Delete a particular image"""
	pass


