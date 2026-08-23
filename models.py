from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from enum import Enum


db = SQLAlchemy()


class UserRole(Enum):
    ADMIN = "Admin"
    STAFF = "Staff"
    USER = "User"


class TrekDifficulty(Enum):
    EASY = "Easy"
    MODERATE = "Moderate"
    HARD = "Hard"


class TrekStatus(Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    OPEN = "Open"
    CLOSED = "Closed"
    STARTED = "Started"
    COMPLETED = "Completed"


class BookingStatus(Enum):
    BOOKED = "Booked"
    CANCELLED = "Cancelled"
    COMPLETED = "Completed"


class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    password = db.Column(db.String(100), nullable=False)

    phone = db.Column(db.String(20))

    role = db.Column(db.Enum(UserRole), nullable=False)

    approved = db.Column(db.Boolean, default=False)

    blacklisted = db.Column(db.Boolean, default=False)

    bookings = db.relationship(
        "Booking",
        backref="user",
        cascade="all, delete-orphan"
    )

    assigned_treks = db.relationship(
        "Trek",
        backref="staff"
    )


class Trek(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    location = db.Column(db.String(100), nullable=False)

    difficulty = db.Column(
        db.Enum(TrekDifficulty),
        nullable=False
    )

    duration = db.Column(db.Integer, nullable=False)

    total_slots = db.Column(db.Integer, nullable=False)

    available_slots = db.Column(db.Integer, nullable=False)

    start_date = db.Column(db.Date, nullable=False)

    end_date = db.Column(db.Date, nullable=False)

    status = db.Column(
        db.Enum(TrekStatus),
        default=TrekStatus.OPEN,
        nullable=False
    )

    description = db.Column(db.Text)

    staff_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id")
    )

    bookings = db.relationship(
        "Booking",
        backref="trek",
        cascade="all, delete-orphan"
    )


class Booking(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    booking_date = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    status = db.Column(
        db.Enum(BookingStatus),
        default=BookingStatus.BOOKED,
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    trek_id = db.Column(
        db.Integer,
        db.ForeignKey("trek.id"),
        nullable=False
    )