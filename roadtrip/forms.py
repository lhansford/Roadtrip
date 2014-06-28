from datetime import datetime

from flask import flash
from flask.ext.wtf import Form
from flask.ext.security import current_user
from wtforms import TextField, FieldList, FormField, DateField, SelectField
from wtforms.validators import Required, Length, Optional

from .models import Trip

class DestinationForm(Form):
	destination = TextField('Destination')

class DayForm(Form):
	destinations = FieldList(FormField(DestinationForm), min_entries = 1)

class TripForm(Form):
	name = TextField('Name', validators = [Required(), Length(max=255)])
	start_date = TextField('Start Date', validators = [Required()])
	start_location = TextField('Start Location', validators = [Required()])

	def validate(self):
		if self.name.data == "" or self.name.data == None:
			flash("You need to name your trip.")
			return False
		if self.name.data in [trip.name for trip in Trip.query.filter_by(user_id=current_user.id).all()]:
			flash("You already have a trip with the name '" + self.name.data + "'. Try a different name.")
			return False
		if self.start_date.data == "" or self.start_date.data == None:
			flash("You need to set a start date for your trip.")
			return False
		if self.start_location.data == "" or self.start_location.data == None:
			flash("You need to set a start location for your trip.")
			return False
		try:	
			datetime.strptime(self.start_date.data, '%a %b %d %Y')
		except:
			flash("The date you selected is invalid.")
			return False
		return True

class TripSettingsForm(Form):
	name = TextField('Name', validators = [Required(), Length(max=255)])
	tileset = SelectField('Tileset', choices=[
		('Acetate.all','Acetate'),
		('Esri.WorldStreetMap','Esri WorldStreetMap'),
		('Esri.DeLorme','Esri DeLorme'),
		('Esri.WorldTopoMap','Esri WorldTopoMap'),
		('Esri.WorldImagery','Esri WorldImagery'),
		('Esri.WorldTerrain','Esri WorldTerrain'),
		('Esri.WorldShadedRelief','Esri WorldShadedRelief'),
		('Esri.WorldPhysical','Esri WorldPhysical'),
		('Esri.OceanBasemap','Esri OceanBasemap'),
		('Esri.NatGeoWorldMap','Esri NatGeoWorldMap'),
		('Esri.WorldGrayCanvas','Esri WorldGrayCanvas'),
		('Hydda.Full','Hydda'),
		('MapQuestOpen.OSM','MapQuest OSM'),
		('MapQuestOpen.Aerial','MapQuest Aerial'),
		('OpenMapSurfer.Mapnik','OpenMapSurfer Roads'),
		('OpenMapSurfer.Mapnik','OpenMapSurfer Grayscale'),
		('OpenStreetMap.Mapnik','OpenStreetMap Mapnik'),
		('OpenStreetMap.BlackAndWhite','OpenStreetMap Black and White'),
		('OpenStreetMap.DE','OpenStreetMap DE'),
		('OpenStreetMap.HOT','OpenStreetMap HOT'),
		('Stamen.Watercolor','Stamen Watercolor'),
		('Stamen.Toner','Stamen Toner'),
		('Stamen.TonerLite','Stamen Toner Lite'),
		('Thunderforest.OpenCycleMap','Thunderforest Open Cycle Map'),
		('Thunderforest.Transport','Thunderforest Transport'),
		('Thunderforest.Landscape','Thunderforest Landscape'),
		('Thunderforest.Outdoors','Thunderforest Outdoors'),
	])