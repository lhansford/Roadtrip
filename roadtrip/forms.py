from datetime import datetime

from flask import flash
from flask.ext.wtf import Form
from wtforms import TextField, FieldList, FormField, DateField
from wtforms.validators import Required, Length, Optional

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