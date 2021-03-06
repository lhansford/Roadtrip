from datetime import datetime, timedelta
import math
import json
import os

from flask import render_template, redirect, url_for, flash, request, session, g, jsonify, send_from_directory
from flask.ext.security import login_required, current_user
from werkzeug.utils import secure_filename

import requests
from sqlalchemy import desc

from roadtrip import app, db, user_datastore
from .models import User, Trip, Day, Location, Image
from .forms import TripForm, DayForm, DestinationForm, TripSettingsForm

@app.route('/')
@login_required
def index():
	trips = Trip.query.filter_by(user_id=current_user.id).all()
	return render_template("index.html",
	 user=current_user,
	 trips=trips,
	 title="Home")

@app.route('/trip/<int:trip_id>', defaults={'day_num': None}, methods=['GET', 'POST'])
@app.route('/trip/<int:trip_id>/<int:day_num>', methods = ['GET', 'POST'])
@login_required
def trip(trip_id, day_num):
	""" Loads a particular trip, with an optional day number to display on page load."""
	if request.method == 'POST':
		upload = request.files['file']
		day_id = request.form['Day']
		day_num = request.form['DayNumber']
		try:
			day = Day.query.get(int(day_id))
			day_num = int(day_num)
		except:
			day = None
			day_num = None
		if upload and allowed_file(upload.filename):
			image = Image(
				name = upload.filename,
				path = "",
				description = "",
				upload_date = datetime.today(),
				user = current_user,
				trip = Trip.query.get(trip_id),
				day = day
			)
			db.session.add(image)
			db.session.flush()
			extension = upload.filename.split('.')[-1]
			filename = secure_filename(str(image.id) + '.' + extension)
			upload.save(os.path.join(app.config['UPLOAD_DIR'], filename))
			image.path = filename
			db.session.commit()
			return redirect(url_for('trip', trip_id=trip_id, day_num=day_num))
	trip = Trip.query.get(trip_id)
	days = Day.query.filter_by(trip=trip).order_by(Day.date).all()
	trip_data = get_trip_data(days)
	routes = []
	locations = []
	for day in trip_data:
		routes += day['route']
		locations += day['locations']
	# locations = list(set(locations))
	total_route = {'route':routes, 'locations':locations}
	total_route['centroid'], total_route['zoom'] = get_route_centroid_and_zoom(total_route['route'])
	images = Image.query.filter_by(trip=trip).all()
	return render_template("trip.html",
	 trip=trip,
	 trip_data=trip_data,
	 total_route=total_route,
	 user=current_user,
	 title=trip.name,
	 images=images,
	 day_num = day_num)

@app.route('/trip/<int:trip_id>/settings', methods = ['GET', 'POST'])
@login_required
def trip_settings(trip_id):
	trip = Trip.query.get(trip_id)
	form = TripSettingsForm(request.form)
	if form.validate_on_submit():
		trip.name = form.name.data
		#The following line will need to change when selecting multiple tilesets is enabled.
		trip.map_tilesets = form.tileset.data
		db.session.commit()
		return redirect(url_for('trip', trip_id=trip_id))
	form.name.data = trip.name
	#The following line will need to change when selecting multiple tilesets is enabled.
	form.tileset.data = trip.get_tilesets()[0]
	return render_template("trip_settings.html",
		trip=trip,
		form=form,
		user=current_user,
		title="Trip Settings")

@app.route('/trip/<int:trip_id>/delete')
@login_required
def delete_trip(trip_id):
	trip = Trip.query.get(trip_id)
	days = Day.query.filter_by(trip=trip).all()
	for day in days:
		for location in Location.query.filter_by(day=day).all():
			db.session.delete(location)
		db.session.delete(day)
	images = Image.query.filter_by(trip=trip).all()
	for image in images:
		os.remove(os.path.join(app.config['UPLOAD_DIR'], image.path))
		db.session.delete(image)
	db.session.delete(trip)
	db.session.commit()
	flash('Your trip was successfully deleted.')
	return redirect(url_for('index'))

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
	return render_template("new_trip.html",
		form = form,
		user=current_user,
		title="Start a new Roadtrip!")

# @app.route('/trip/<int:trip_id>/edit')
# @login_required
# def edit_trip(trip_id):
# 	""" Edit a given road trip. """

# 	trip = Trip.query.get(trip_id)
# 	#Redirect if not the current user
# 	if current_user != trip.user:
# 		return redirect('index')
# 	days = Day.query.filter_by(trip=trip).order_by(Day.date).all()
# 	trip_data = get_trip_data(days)
# 	return render_template("edit_trip.html", trip=trip, days=trip_data)

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
	return render_template("edit_day.html", trip=trip, day=day, day_num=day_num, locations=locations, user=current_user)

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
		"num": Day.query.filter_by(trip=trip).count(),
		"date": new_day.date.strftime("%a, %d %B %Y")
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
	return jsonify({"name":new_location.name, "id":new_location.id})

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

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
	image = Image.query.get(int(filename.split('.')[0]))
	if current_user != image.user:
		return redirect(url_for('index'))
	return send_from_directory(app.config['UPLOAD_DIR'], filename)

@app.route('/trip/image/<int:image_id>')
@login_required
def image(image_id):
	image = Image.query.get(image_id)
	if current_user != image.trip.user:
		return redirect('index')
	return render_template("image.html", user=current_user, image=image)

@app.route('/trip/image/<int:image_id>/delete')
@login_required
def delete_image(image_id):
	""" Deletes the Image represented in the database by the given id. """
	image = Image.query.get(image_id)
	trip = image.trip
	db.session.delete(image)
	db.session.commit()
	flash('The image was successfully deleted.')
	return redirect(url_for('trip', trip_id = trip.id))

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
	if len(locations) == 0:
		return []
	if len(locations) == 1:
		return [(locations[0]['latitude'], locations[0]['longitude'])]
	url = "http://router.project-osrm.org/viaroute?loc="
	for location in locations:
		url += (str(location['latitude']) + ',' + str(location['longitude']) + '&loc=')
	r = requests.get(url[:-5]) #Remove last '&loc='
	if r.json()['status'] == 207:
		#Issue finding route
		return []
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

def get_route_centroid_and_zoom(route):
	""" Returns the centroid and zoom level for the locations in route. """
	if len(route) == 1:
		return (route[0][0],route[0][1]), 3
	elif len(route) == 0:
		return (0,0), 2
	latitudes = [l[0] for l in route]
	longitudes = [l[1] for l in route]
	lat = (max(latitudes) + min(latitudes)) / 2
	lng = (max(longitudes) + min(longitudes)) / 2
	#Calculate zoom level
	difference = max([max(latitudes) - min(latitudes), max(longitudes) - min(longitudes)])
	x, zoom = 360, 0
	while difference < x:
		x /= 2
		zoom += 1
	return (lat, lng), zoom

def get_trip_data(days):
	"""Takes an object days containing a number of Day objects and creates
	a dictionary of data for a trip.
	"""
	trip_data = []
	num = 1
	for day in days:
		d = {}
		d['id'] = day.id
		d['date'] = day.date.strftime("%a, %d %B %Y")
		d['num'] = num
		#Need to convert object to dict so JS can convert to JSON later on.
		d['locations'] = [{'latitude':l.latitude, 'longitude':l.longitude, 'name':l.name} for l in Location.query.filter_by(day=day).order_by(Location.order).all()]
		d['route'] = get_route(d['locations'])
		d['centroid'], d['zoom'] = get_route_centroid_and_zoom(d['route'])
		trip_data.append(d)
		num += 1
	return trip_data

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']