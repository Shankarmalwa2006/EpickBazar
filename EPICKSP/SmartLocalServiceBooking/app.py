import os
import sqlite3
from functools import wraps
from datetime import datetime
from typing import Optional, Dict, Any, List

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    g,
    abort,
)
from werkzeug.security import generate_password_hash, check_password_hash


# ------------------------------------------------------------
# App setup
# ------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)

# NOTE:
# - In production, ALWAYS set a strong secret key via environment variable.
# - For beginners/local dev, this fallback makes the app run out-of-the-box.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")


# ------------------------------------------------------------
# Database helpers (SQLite)
# ------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    """Get a request-scoped SQLite connection (available as g.db)."""
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Access columns like dict keys
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(error=None) -> None:
    """Close the SQLite connection when the request ends."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def db_query(sql: str, params: tuple = (), one: bool = False):
    """Run a SELECT query and return sqlite3.Row(s)."""
    cur = get_db().execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    return rows[0] if one and rows else rows


def db_execute(sql: str, params: tuple = ()) -> int:
    """Run an INSERT/UPDATE/DELETE query and return lastrowid (if any)."""
    conn = get_db()
    cur = conn.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id


# ------------------------------------------------------------
# Authentication & authorization helpers
# ------------------------------------------------------------

def set_session_user(user_row: sqlite3.Row) -> None:
    """Store minimal user info in session (session-based auth)."""
    session.clear()
    session["user_id"] = user_row["id"]
    session["role"] = user_row["role"]
    session["name"] = user_row["name"]


def current_user() -> Optional[Dict[str, Any]]:
    """
    Load the logged-in user from DB (cached in g.current_user).
    Returns None if not logged in.
    """
    if "current_user" in g:
        return g.current_user

    user_id = session.get("user_id")
    if not user_id:
        g.current_user = None
        return None

    user = db_query(
        "SELECT id, name, email, role FROM users WHERE id = ?",
        (user_id,),
        one=True,
    )
    g.current_user = dict(user) if user else None
    return g.current_user


@app.context_processor
def inject_user():
    """Make shared helpers available in all templates."""
    return {"current_user": current_user(), "datetime": datetime}


def login_required(view_func):
    """Protect routes that require a logged-in user."""

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapper


def role_required(*allowed_roles: str):
    """Protect routes by user role (user/provider/admin)."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login", next=request.path))

            role = session.get("role")
            if role not in allowed_roles:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapper

    return decorator


# ------------------------------------------------------------
# Basic pages
# ------------------------------------------------------------

@app.route("/")
def index():
    return redirect(url_for("services"))


@app.route("/dashboard")
@login_required
def dashboard():
    role = session.get("role")
    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    return render_template("dashboard.html", role=role)


# ------------------------------------------------------------
# Auth: Register / Login / Logout
# ------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    # Admin accounts are not created here. Use init_db.py to seed an admin.
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        role = request.form.get("role") or "user"

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if role not in ("user", "provider"):
            flash("Invalid role selection.", "danger")
            return render_template("register.html")

        try:
            hashed = generate_password_hash(password)
            db_execute(
                "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                (name, email, hashed, role),
            )
        except sqlite3.IntegrityError:
            flash("Email is already registered. Please log in instead.", "warning")
            return render_template("register.html")

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("login.html")

        user = db_query(
            "SELECT id, name, email, password, role FROM users WHERE email = ?",
            (email,),
            one=True,
        )
        if not user or not check_password_hash(user["password"], password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        set_session_user(user)
        flash(f"Welcome back, {user['name']}!", "success")

        next_url = request.args.get("next")
        return redirect(next_url or url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ------------------------------------------------------------
# Services
# ------------------------------------------------------------

@app.route("/services")
def services():
    """
    Public: view all services.
    Logged-in users can book.
    Providers can also see "Add Service" link (handled in template).
    """
    services_rows = db_query(
        """
        SELECT
            s.id,
            s.provider_id,
            s.service_type,
            s.category,
            s.price,
            s.description,
            u.name AS provider_name
        FROM services s
        JOIN users u ON u.id = s.provider_id
        ORDER BY s.id DESC
        """
    )
    return render_template("services.html", services=services_rows)


@app.route("/services/add", methods=["GET", "POST"])
@role_required("provider")
def add_service():
    if request.method == "POST":
        service_type = (request.form.get("service_type") or "").strip()
        category = (request.form.get("category") or "").strip()
        price_raw = (request.form.get("price") or "").strip()
        description = (request.form.get("description") or "").strip()

        if not service_type or not category or not price_raw or not description:
            flash("All fields are required.", "danger")
            return render_template("add_service.html")

        try:
            price = float(price_raw)
            if price < 0:
                raise ValueError
        except ValueError:
            flash("Price must be a valid non-negative number.", "danger")
            return render_template("add_service.html")

        db_execute(
            """
            INSERT INTO services (provider_id, service_type, category, price, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session["user_id"], service_type, category, price, description),
        )
        flash("Service added successfully.", "success")
        return redirect(url_for("services"))

    return render_template("add_service.html")


# ------------------------------------------------------------
# Bookings (User)
# ------------------------------------------------------------

@app.route("/services/<int:service_id>/book", methods=["POST"])
@role_required("user")
def book_service(service_id: int):
    booking_date = (request.form.get("booking_date") or "").strip()
    address = (request.form.get("address") or "").strip()

    if not booking_date or not address:
        flash("Booking date and address are required.", "danger")
        return redirect(url_for("services"))

    # Basic server-side date validation (client-side JS adds better UX).
    try:
        datetime.strptime(booking_date, "%Y-%m-%d")
    except ValueError:
        flash("Invalid booking date format.", "danger")
        return redirect(url_for("services"))

    service = db_query("SELECT id FROM services WHERE id = ?", (service_id,), one=True)
    if not service:
        flash("Service not found.", "danger")
        return redirect(url_for("services"))

    db_execute(
        """
        INSERT INTO bookings (user_id, service_id, booking_date, address, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session["user_id"], service_id, booking_date, address, "Pending"),
    )
    flash("Booking request created successfully.", "success")
    return redirect(url_for("my_bookings"))


@app.route("/bookings")
@role_required("user")
def my_bookings():
    rows = db_query(
        """
        SELECT
            b.id,
            b.booking_date,
            b.address,
            b.status,
            s.service_type,
            s.category,
            s.price,
            u.name AS provider_name
        FROM bookings b
        JOIN services s ON s.id = b.service_id
        JOIN users u ON u.id = s.provider_id
        WHERE b.user_id = ?
        ORDER BY b.id DESC
        """,
        (session["user_id"],),
    )
    return render_template("bookings.html", mode="user", bookings=rows)


# ------------------------------------------------------------
# Booking Requests (Provider)
# ------------------------------------------------------------

@app.route("/provider/bookings")
@role_required("provider")
def provider_bookings():
    rows = db_query(
        """
        SELECT
            b.id,
            b.booking_date,
            b.address,
            b.status,
            s.service_type,
            s.category,
            s.price,
            u.name AS user_name,
            u.email AS user_email
        FROM bookings b
        JOIN services s ON s.id = b.service_id
        JOIN users u ON u.id = b.user_id
        WHERE s.provider_id = ?
        ORDER BY b.id DESC
        """,
        (session["user_id"],),
    )
    return render_template("bookings.html", mode="provider", bookings=rows)


@app.route("/provider/bookings/<int:booking_id>/status", methods=["POST"])
@role_required("provider")
def update_booking_status(booking_id: int):
    new_status = (request.form.get("status") or "").strip()
    allowed = {"Pending", "Accepted", "Completed", "Rejected"}
    if new_status not in allowed:
        flash("Invalid status.", "danger")
        return redirect(url_for("provider_bookings"))

    # Ensure provider owns the service for this booking.
    booking = db_query(
        """
        SELECT b.id
        FROM bookings b
        JOIN services s ON s.id = b.service_id
        WHERE b.id = ? AND s.provider_id = ?
        """,
        (booking_id, session["user_id"]),
        one=True,
    )
    if not booking:
        flash("Booking not found (or not authorized).", "danger")
        return redirect(url_for("provider_bookings"))

    db_execute("UPDATE bookings SET status = ? WHERE id = ?", (new_status, booking_id))
    flash("Booking status updated.", "success")
    return redirect(url_for("provider_bookings"))


# ------------------------------------------------------------
# Admin
# ------------------------------------------------------------

@app.route("/admin/dashboard")
@role_required("admin")
def admin_dashboard():
    total_users = db_query("SELECT COUNT(*) AS c FROM users", one=True)["c"]
    total_services = db_query("SELECT COUNT(*) AS c FROM services", one=True)["c"]
    total_bookings = db_query("SELECT COUNT(*) AS c FROM bookings", one=True)["c"]

    users_rows = db_query(
        "SELECT id, name, email, role FROM users ORDER BY id DESC"
    )
    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_services=total_services,
        total_bookings=total_bookings,
        users=users_rows,
    )


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@role_required("admin")
def admin_delete_user(user_id: int):
    # Prevent deleting yourself (avoid locking admin out).
    if user_id == session.get("user_id"):
        flash("You cannot delete your own account.", "warning")
        return redirect(url_for("admin_dashboard"))

    target = db_query("SELECT id, role FROM users WHERE id = ?", (user_id,), one=True)
    if not target:
        flash("User not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    # Safety: don't allow deleting other admins in this beginner app.
    if target["role"] == "admin":
        flash("Admin accounts cannot be deleted from the UI.", "warning")
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    try:
        conn.execute("BEGIN")

        # Remove bookings made by this user
        conn.execute("DELETE FROM bookings WHERE user_id = ?", (user_id,))

        # If provider: remove bookings for their services, then services
        conn.execute(
            """
            DELETE FROM bookings
            WHERE service_id IN (SELECT id FROM services WHERE provider_id = ?)
            """,
            (user_id,),
        )
        conn.execute("DELETE FROM services WHERE provider_id = ?", (user_id,))

        # Finally remove user
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    flash("User deleted successfully.", "success")
    return redirect(url_for("admin_dashboard"))


# ------------------------------------------------------------
# Error pages
# ------------------------------------------------------------

@app.errorhandler(403)
def forbidden(_):
    return render_template("index.html", error="403 Forbidden: You are not allowed to access this page."), 403


@app.errorhandler(404)
def not_found(_):
    return render_template("index.html", error="404 Not Found: The page you requested does not exist."), 404


@app.errorhandler(sqlite3.OperationalError)
def db_error(err):
    # Common beginner issue: database not initialized yet.
    msg = (
        "Database error. Did you run init_db.py to create the tables?\n\n"
        f"Details: {err}"
    )
    return render_template("index.html", error=msg), 500


if __name__ == "__main__":
    # debug=True is helpful while learning; turn it off for production.
    app.run(debug=True)
