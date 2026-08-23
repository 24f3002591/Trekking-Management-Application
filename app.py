from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user
from flask_login import login_required, current_user
from datetime import datetime

from models import db
from models import User, Trek, Booking
from models import UserRole, TrekDifficulty
from models import TrekStatus, BookingStatus


app = Flask(__name__)

app.config["SECRET_KEY"] = "trekking123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///trekking.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_only():
    if current_user.role != UserRole.ADMIN:
        flash("Access denied.")
        return False
    return True


def staff_only():
    if current_user.role != UserRole.STAFF:
        flash("Access denied.")
        return False
    return True


def user_only():
    if current_user.role != UserRole.USER:
        flash("Access denied.")
        return False
    return True


@app.route("/")
def home():
    treks = Trek.query.filter_by(
        status=TrekStatus.OPEN
    ).all()

    return render_template(
        "home.html",
        treks=treks
    )


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]
        role = request.form["role"]

        if User.query.filter_by(email=email).first():
            flash("Email already registered.")
            return redirect(url_for("register"))

        if role == "staff":
            user_role = UserRole.STAFF
            approved = False
        else:
            user_role = UserRole.USER
            approved = True

        user = User(
            name=name,
            email=email,
            phone=phone,
            password=password,
            role=user_role,
            approved=approved
        )

        db.session.add(user)
        db.session.commit()

        if user_role == UserRole.STAFF:
            flash("Registration successful. Wait for admin approval.")
        else:
            flash("Registration successful.")

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user is None or user.password != password:
            flash("Invalid email or password.")
            return redirect(url_for("login"))

        if user.blacklisted:
            flash("Your account is blacklisted.")
            return redirect(url_for("login"))

        if user.role == UserRole.STAFF and not user.approved:
            flash("Wait for admin approval.")
            return redirect(url_for("login"))

        login_user(user)

        if user.role == UserRole.ADMIN:
            return redirect(url_for("admin_dashboard"))

        if user.role == UserRole.STAFF:
            return redirect(url_for("staff_dashboard"))

        return redirect(url_for("user_dashboard"))

    return render_template("login.html")



@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(url_for("home"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    if request.method == "POST":

        current_user.name = request.form["name"]
        current_user.phone = request.form["phone"]

        db.session.commit()

        flash("Profile updated.")

        return redirect(url_for("profile"))

    return render_template("profile.html")


@app.route("/admin")
@login_required
def admin_dashboard():

    if not admin_only():
        return redirect(url_for("home"))

    total_treks = Trek.query.count()

    total_users = User.query.filter_by(
        role=UserRole.USER
    ).count()

    total_staff = User.query.filter_by(
        role=UserRole.STAFF
    ).count()

    total_bookings = Booking.query.count()

    return render_template(
        "admin/dashboard.html",
        total_treks=total_treks,
        total_users=total_users,
        total_staff=total_staff,
        total_bookings=total_bookings
    )


@app.route("/admin/treks")
@login_required
def manage_treks():

    if not admin_only():
        return redirect(url_for("home"))

    treks = Trek.query.all()

    return render_template(
        "admin/treks.html",
        treks=treks
    )


@app.route("/admin/treks/add", methods=["GET", "POST"])
@login_required
def add_trek():

    if not admin_only():
        return redirect(url_for("home"))

    staff = User.query.filter_by(
        role=UserRole.STAFF,
        approved=True,
        blacklisted=False
    ).all()

    if request.method == "POST":

        slots = int(request.form["slots"])

        if slots <= 0:
            flash("Slots must be greater than zero.")
            return redirect(url_for("add_trek"))

        start_date = datetime.strptime(
            request.form["start_date"],
            "%Y-%m-%d"
        ).date()

        end_date = datetime.strptime(
            request.form["end_date"],
            "%Y-%m-%d"
        ).date()

        if end_date < start_date:
            flash("End date cannot be before start date.")
            return redirect(url_for("add_trek"))

        trek = Trek(
            name=request.form["name"],
            location=request.form["location"],
            difficulty=TrekDifficulty(
                request.form["difficulty"]
            ),
            duration=int(request.form["duration"]),
            total_slots=slots,
            available_slots=slots,
            start_date=start_date,
            end_date=end_date,
            status=TrekStatus.OPEN,
            description=request.form["description"]
        )

        staff_id = request.form.get("staff_id")

        if staff_id:
            trek.staff_id = int(staff_id)

        db.session.add(trek)
        db.session.commit()

        flash("Trek added successfully.")

        return redirect(url_for("manage_treks"))

    return render_template(
        "admin/add_trek.html",
        difficulties=TrekDifficulty,
        staff=staff
    )


@app.route("/admin/treks/edit/<int:trek_id>", methods=["GET", "POST"])
@login_required
def edit_trek(trek_id):

    if not admin_only():
        return redirect(url_for("home"))

    trek = Trek.query.get_or_404(trek_id)

    staff = User.query.filter_by(
        role=UserRole.STAFF,
        approved=True,
        blacklisted=False
    ).all()

    if request.method == "POST":

        new_slots = int(request.form["slots"])

        booked = trek.total_slots - trek.available_slots

        if new_slots < booked:
            flash("Slots cannot be less than current bookings.")
            return redirect(
                url_for("edit_trek", trek_id=trek.id)
            )

        start_date = datetime.strptime(
            request.form["start_date"],
            "%Y-%m-%d"
        ).date()

        end_date = datetime.strptime(
            request.form["end_date"],
            "%Y-%m-%d"
        ).date()

        if end_date < start_date:
            flash("End date cannot be before start date.")
            return redirect(
                url_for("edit_trek", trek_id=trek.id)
            )

        trek.name = request.form["name"]
        trek.location = request.form["location"]

        trek.difficulty = TrekDifficulty(
            request.form["difficulty"]
        )

        trek.duration = int(request.form["duration"])

        trek.total_slots = new_slots
        trek.available_slots = new_slots - booked

        trek.start_date = start_date
        trek.end_date = end_date

        trek.description = request.form["description"]

        staff_id = request.form.get("staff_id")

        if staff_id:
            trek.staff_id = int(staff_id)
        else:
            trek.staff_id = None

        db.session.commit()

        flash("Trek updated successfully.")

        return redirect(url_for("manage_treks"))

    return render_template(
        "admin/edit_trek.html",
        trek=trek,
        difficulties=TrekDifficulty,
        staff=staff
    )


@app.route("/admin/treks/delete/<int:trek_id>")
@login_required
def delete_trek(trek_id):

    if not admin_only():
        return redirect(url_for("home"))

    trek = Trek.query.get_or_404(trek_id)

    if trek.bookings:
        flash("Trek cannot be deleted because it has bookings.")
        return redirect(url_for("manage_treks"))

    db.session.delete(trek)
    db.session.commit()

    flash("Trek deleted.")

    return redirect(url_for("manage_treks"))


@app.route("/admin/staff")
@login_required
def manage_staff():

    if not admin_only():
        return redirect(url_for("home"))

    search = request.args.get("search", "")

    query = User.query.filter_by(
        role=UserRole.STAFF
    )

    if search:
        query = query.filter(
            User.name.contains(search)
        )

    staff = query.all()

    return render_template(
        "admin/staff.html",
        staff=staff,
        search=search
    )


@app.route("/admin/staff/approve/<int:user_id>")
@login_required
def approve_staff(user_id):

    if not admin_only():
        return redirect(url_for("home"))

    staff = User.query.get_or_404(user_id)

    if staff.role != UserRole.STAFF:
        flash("Invalid staff member.")
        return redirect(url_for("manage_staff"))

    staff.approved = True

    db.session.commit()

    flash("Staff approved.")

    return redirect(url_for("manage_staff"))


@app.route("/admin/staff/blacklist/<int:user_id>")
@login_required
def blacklist_staff(user_id):

    if not admin_only():
        return redirect(url_for("home"))

    staff = User.query.get_or_404(user_id)

    staff.blacklisted = not staff.blacklisted

    db.session.commit()

    if staff.blacklisted:
        flash("Staff blacklisted.")
    else:
        flash("Staff removed from blacklist.")

    return redirect(url_for("manage_staff"))

@app.route("/admin/users")
@login_required
def manage_users():

    if not admin_only():
        return redirect(url_for("home"))

    search = request.args.get("search", "")

    query = User.query.filter_by(
        role=UserRole.USER
    )

    if search:
        query = query.filter(
            User.name.contains(search)
        )

    users = query.all()

    return render_template(
        "admin/users.html",
        users=users,
        search=search
    )


@app.route("/admin/users/blacklist/<int:user_id>")
@login_required
def blacklist_user(user_id):

    if not admin_only():
        return redirect(url_for("home"))

    user = User.query.get_or_404(user_id)

    user.blacklisted = not user.blacklisted

    db.session.commit()

    if user.blacklisted:
        flash("User blacklisted.")
    else:
        flash("User removed from blacklist.")

    return redirect(url_for("manage_users"))


@app.route("/admin/bookings")
@login_required
def admin_bookings():

    if not admin_only():
        return redirect(url_for("home"))

    bookings = Booking.query.order_by(
        Booking.booking_date.desc()
    ).all()

    return render_template(
        "admin/bookings.html",
        bookings=bookings
    )


@app.route("/staff")
@login_required
def staff_dashboard():

    if not staff_only():
        return redirect(url_for("home"))

    treks = Trek.query.filter_by(
        staff_id=current_user.id
    ).all()

    return render_template(
        "staff/dashboard.html",
        treks=treks
    )


@app.route("/staff/trek/<int:trek_id>", methods=["GET", "POST"])
@login_required
def staff_trek(trek_id):

    if not staff_only():
        return redirect(url_for("home"))

    trek = Trek.query.get_or_404(trek_id)

    if trek.staff_id != current_user.id:
        flash("This trek is not assigned to you.")
        return redirect(url_for("staff_dashboard"))

    if request.method == "POST":

        slots = int(request.form["slots"])

        booked = trek.total_slots - trek.available_slots

        if slots < booked:
            flash("Slots cannot be less than registered users.")
            return redirect(
                url_for("staff_trek", trek_id=trek.id)
            )

        trek.total_slots = slots
        trek.available_slots = slots - booked

        trek.status = TrekStatus(
            request.form["status"]
        )
        if trek.status == TrekStatus.COMPLETED:

            for booking in trek.bookings:

                if booking.status == BookingStatus.BOOKED:
                    booking.status = BookingStatus.COMPLETED

        db.session.commit()

        flash("Trek updated.")

        return redirect(
            url_for("staff_trek", trek_id=trek.id)
        )

    participants = Booking.query.filter_by(
        trek_id=trek.id,
        status=BookingStatus.BOOKED
    ).all()

    return render_template(
        "staff/trek.html",
        trek=trek,
        participants=participants,
        statuses=[
            TrekStatus.OPEN,
            TrekStatus.CLOSED,
            TrekStatus.STARTED,
            TrekStatus.COMPLETED
        ]
    )


@app.route("/user")
@login_required
def user_dashboard():

    if not user_only():
        return redirect(url_for("home"))

    search = request.args.get("search", "")
    difficulty = request.args.get("difficulty", "")

    query = Trek.query.filter_by(
        status=TrekStatus.OPEN
    )

    if search:
        query = query.filter(
            (Trek.name.ilike("%" + search + "%")) |
            (Trek.location.ilike("%" + search + "%"))
        )

    if difficulty:
        query = query.filter(
            Trek.difficulty == TrekDifficulty(difficulty)
        )

    treks = query.all()

    bookings = Booking.query.filter_by(
        user_id=current_user.id
    ).all()

    booked_trek_ids = []

    for booking in bookings:
        if booking.status == BookingStatus.BOOKED:
            booked_trek_ids.append(booking.trek_id)

    return render_template(
        "user/dashboard.html",
        treks=treks,
        bookings=bookings,
        booked_trek_ids=booked_trek_ids,
        difficulties=TrekDifficulty,
        search=search,
        difficulty=difficulty
    )
    

@app.route("/user/book/<int:trek_id>")
@login_required
def book_trek(trek_id):

    if not user_only():
        return redirect(url_for("home"))

    trek = Trek.query.get_or_404(trek_id)

    if trek.status != TrekStatus.OPEN:
        flash("This trek is not open for booking.")
        return redirect(url_for("user_dashboard"))

    if trek.available_slots <= 0:
        flash("No slots available.")
        return redirect(url_for("user_dashboard"))

    old_booking = Booking.query.filter_by(
        user_id=current_user.id,
        trek_id=trek.id,
    ).first()

    if old_booking:
        flash("You have already booked this trek.")
        return redirect(url_for("user_dashboard"))

    booking = Booking(
        user_id=current_user.id,
        trek_id=trek.id,
        status=BookingStatus.BOOKED
    )

    trek.available_slots -= 1

    db.session.add(booking)
    db.session.commit()

    flash("Trek booked successfully.")

    return redirect(url_for("user_dashboard"))


@app.route("/user/history")
@login_required
def booking_history():

    if not user_only():
        return redirect(url_for("home"))

    bookings = Booking.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Booking.booking_date.desc()
    ).all()

    return render_template(
        "user/history.html",
        bookings=bookings
    )


with app.app_context():

    db.create_all()
    
    staff1 = User.query.filter_by(email="ramesh@trekmate.com").first()

    if staff1 is None:
        staff1 = User(
            name="Ramesh Gurung",
            email="ramesh@trekmate.com",
            phone="9876543210",
            password="ramesh123",
            role=UserRole.STAFF,
            approved=True,
            blacklisted=False
        )

        db.session.add(staff1)


    staff2 = User.query.filter_by(email="anita@trekmate.com").first()

    if staff2 is None:
        staff2 = User(
            name="Anita Sharma",
            email="anita@trekmate.com",
            phone="9876543211",
            password="anita123",
            role=UserRole.STAFF,
            approved=True,
            blacklisted=False
        )

        db.session.add(staff2)


    user1 = User.query.filter_by(email="priya@gmail.com").first()

    if user1 is None:
        user1 = User(
            name="Priya Sharma",
            email="priya@gmail.com",
            phone="9876543212",
            password="priya123",
            role=UserRole.USER,
            approved=True,
            blacklisted=False
        )

        db.session.add(user1)


    user2 = User.query.filter_by(email="arjun@gmail.com").first()

    if user2 is None:
        user2 = User(
            name="Arjun Nair",
            email="arjun@gmail.com",
            phone="9876543213",
            password="arjun123",
            role=UserRole.USER,
            approved=True,
            blacklisted=False
        )

        db.session.add(user2)


    user3 = User.query.filter_by(email="meera@gmail.com").first()

    if user3 is None:
        user3 = User(
            name="Meera Dutta",
            email="meera@gmail.com",
            phone="9876543214",
            password="meera123",
            role=UserRole.USER,
            approved=True,
            blacklisted=False
        )

        db.session.add(user3)


    db.session.commit()
    
    if Trek.query.count() == 0:

        trek1 = Trek(
            name="Kedarnath Trek",
            location="Uttarakhand",
            difficulty=TrekDifficulty.HARD,
            duration=6,
            total_slots=15,
            available_slots=15,
            start_date=datetime(2026, 8, 20).date(),
            end_date=datetime(2026, 8, 25).date(),
            status=TrekStatus.OPEN,
            description="A beautiful mountain trek to Kedarnath."
        )

        trek2 = Trek(
            name="Netravati Trek",
            location="Karnataka",
            difficulty=TrekDifficulty.MODERATE,
            duration=3,
            total_slots=20,
            available_slots=20,
            start_date=datetime(2026, 9, 5).date(),
            end_date=datetime(2026, 9, 7).date(),
            status=TrekStatus.OPEN,
            description="A green forest trek with scenic views."
        )

        trek3 = Trek(
            name="Kumara Parvatha",
            location="Karnataka",
            difficulty=TrekDifficulty.HARD,
            duration=2,
            total_slots=12,
            available_slots=12,
            start_date=datetime(2026, 9, 15).date(),
            end_date=datetime(2026, 9, 16).date(),
            status=TrekStatus.OPEN,
            description="A challenging trek through the Western Ghats."
        )

        trek4 = Trek(
            name="Triund Trek",
            location="Himachal Pradesh",
            difficulty=TrekDifficulty.MODERATE,
            duration=2,
            total_slots=18,
            available_slots=18,
            start_date=datetime(2026, 10, 2).date(),
            end_date=datetime(2026, 10, 3).date(),
            status=TrekStatus.OPEN,
            description="A simple Himalayan trek with beautiful valley views."
        )

        db.session.add_all([
            trek1,
            trek2,
            trek3,
            trek4
        ])

    db.session.commit()

    admin = User.query.filter_by(
        email="admin@trek.com"
    ).first()

    if admin is None:

        admin = User(
            name="Admin",
            email="admin@trek.com",
            phone="9999999999",
            password="admin123",
            role=UserRole.ADMIN,
            approved=True,
            blacklisted=False
        )

        db.session.add(admin)
        db.session.commit()


if __name__ == "__main__":
    app.run(debug=True)