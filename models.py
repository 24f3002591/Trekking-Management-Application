from sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(20), unique=True, nullable=False)
  email = db.Column(db.String(120), unique=True, nullable=False)
  
class trek(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(100), nullable=False)
  location = db.Column(db.String(100), nullable=False)
  description = db.Column(db.Text, nullable=False)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
  
class Booking(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  trek_id = db.Column(db.Integer, db.ForeignKey('trek.id'), nullable=False)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
  booking_date = db.Column(db.DateTime, nullable=False)