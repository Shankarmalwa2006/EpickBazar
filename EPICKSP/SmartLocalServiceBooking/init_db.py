import os
import sqlite3

from werkzeug.security import generate_password_hash


"""
init_db.py

Creates SQLite database (database.db) and required tables:
- users
- services
- bookings

Also seeds a default admin account (if it doesn't exist yet).
Run:
  py init_db.py
"""


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'provider', 'admin'))
);

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER NOT NULL,
    service_type TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL CHECK(price >= 0),
    description TEXT NOT NULL,
    FOREIGN KEY (provider_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    booking_date TEXT NOT NULL,
    address TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('Pending', 'Accepted', 'Completed', 'Rejected')) DEFAULT 'Pending',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_services_provider_id ON services(provider_id);
CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_service_id ON bookings(service_id);
"""


def seed_users_and_services(conn: sqlite3.Connection) -> None:
    """
    Seed:
    - 1 admin
    - 4 providers
    - 3 normal users
    - 2 services per provider
    This function is safe to run multiple times (it checks by email/name).
    """
    # --- Admin ---
    admin_name = "Admin"
    admin_email = "admin@smartlocal.com"
    admin_password = "Admin@123"

    cur = conn.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
    exists = cur.fetchone()
    cur.close()

    if not exists:
        conn.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (admin_name, admin_email, generate_password_hash(admin_password), "admin"),
        )
        print("Seeded admin account:")
        print(f"  Email: {admin_email}")
        print(f"  Password: {admin_password}")
    else:
        print("Admin account already exists.")

    # --- Providers ---
    providers = [
        {
            "name": "Amit Verma",
            "email": "amit.electrician@gmail.com",
            "password": "Amit@123",
        },
        {
            "name": "Suresh Patel",
            "email": "suresh.plumber@gmail.com",
            "password": "Suresh@123",
        },
        {
            "name": "Imran Khan",
            "email": "imran.acrepair@gmail.com",
            "password": "Imran@123",
        },
        {
            "name": "Rohan Mehta",
            "email": "rohan.carpenter@gmail.com",
            "password": "Rohan@123",
        },
    ]

    provider_ids = {}
    for p in providers:
        cur = conn.execute("SELECT id FROM users WHERE email = ?", (p["email"],))
        row = cur.fetchone()
        cur.close()
        if row:
            provider_ids[p["email"]] = row[0]
            continue

        cur = conn.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, 'provider')",
            (p["name"], p["email"], generate_password_hash(p["password"])),
        )
        provider_ids[p["email"]] = cur.lastrowid
        print(f"Seeded provider: {p['name']} ({p['email']})")

    # --- Normal users ---
    users = [
        {
            "name": "Priya Desai",
            "email": "priya.desai@gmail.com",
            "password": "Priya@123",
        },
        {
            "name": "Neha Singh",
            "email": "neha.singh@gmail.com",
            "password": "Neha@123",
        },
        {
            "name": "Arjun Kulkarni",
            "email": "arjun.kulkarni@gmail.com",
            "password": "Arjun@123",
        },
    ]

    for u in users:
        cur = conn.execute("SELECT id FROM users WHERE email = ?", (u["email"],))
        row = cur.fetchone()
        cur.close()
        if row:
            continue
        conn.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, 'user')",
            (u["name"], u["email"], generate_password_hash(u["password"])),
        )
        print(f"Seeded user: {u['name']} ({u['email']})")

    # --- Services ---
    # Map provider email -> list of (service_type, category, price, description)
    services_by_provider = {
        # Amit - electrical + smart home + emergency
        "amit.electrician@gmail.com": [
            (
                "Electrician",
                "Home Maintenance",
                500,
                "Electrical wiring repair, switchboard installation, fan fitting, and minor power issues at your home.",
            ),
            (
                "WiFi Router Setup",
                "Technical Services",
                400,
                "Router installation, network setup, password configuration, and signal optimization.",
            ),
            (
                "Smart Home Setup",
                "Technical Services",
                2500,
                "Installation of smart lights, voice assistants, CCTV, and basic home automation systems.",
            ),
            (
                "CCTV Installation",
                "Security Services",
                5000,
                "Complete CCTV camera setup with DVR configuration and remote viewing access.",
            ),
            (
                "Emergency Electrician",
                "Emergency Services",
                900,
                "Immediate electrical fault repair within 60 minutes for urgent issues.",
            ),
            (
                "Emergency Plumbing",
                "Emergency Services",
                850,
                "Urgent pipe burst and major leakage repair service for homes and small offices.",
            ),
        ],
        # Suresh - plumbing + cleaning + logistics
        "suresh.plumber@gmail.com": [
            (
                "Plumber",
                "Home Maintenance",
                450,
                "Pipe leakage repair, tap replacement, drainage issues, and bathroom fittings installation.",
            ),
            (
                "Home Deep Cleaning",
                "Cleaning Services",
                2500,
                "Complete house deep cleaning including kitchen, bathroom, and floor sanitization.",
            ),
            (
                "Office Cleaning",
                "Cleaning Services",
                4000,
                "Full office cleaning including desks, washrooms, glass, and complete sanitization.",
            ),
            (
                "Water Tank Cleaning",
                "Cleaning Services",
                1200,
                "Deep cleaning and disinfection of overhead and underground water tanks.",
            ),
            (
                "Packers & Movers",
                "Transport Services",
                7000,
                "Professional packing and relocation service for within-city moves.",
            ),
            (
                "Local Delivery Service",
                "Transport Services",
                300,
                "Small parcel and document pickup and delivery within city limits.",
            ),
        ],
        # Imran - AC + computers + office / data
        "imran.acrepair@gmail.com": [
            (
                "AC Repair & Service",
                "Home Maintenance",
                800,
                "AC gas refill, cooling issue diagnosis, regular servicing, and installation support.",
            ),
            (
                "Computer Repair",
                "Technical Services",
                700,
                "Hardware troubleshooting, OS installation, virus removal, and performance optimization.",
            ),
            (
                "Data Recovery Service",
                "Technical Services",
                3000,
                "Recover deleted files and data from damaged hard drives, SSDs, or USB devices.",
            ),
            (
                "Office IT Setup",
                "Business Services",
                6000,
                "Setup of office computers, network wiring, routers, printers, and basic security.",
            ),
            (
                "Accounting Consultation",
                "Business Services",
                2000,
                "GST filing, tax consultation, and small business financial advisory session.",
            ),
        ],
        # Rohan - carpentry + home improvement + events + personal/beauty
        "rohan.carpenter@gmail.com": [
            (
                "Carpenter",
                "Home Maintenance",
                600,
                "Furniture repair, wooden door fixing, cabinet installation, and modular adjustments.",
            ),
            (
                "Sofa Cleaning",
                "Cleaning Services",
                1200,
                "Deep sofa shampoo cleaning with stain removal and fabric sanitization.",
            ),
            (
                "Modular Kitchen Installation",
                "Home Improvement",
                15000,
                "Complete modular kitchen setup including cabinets, fittings, and installation support.",
            ),
            (
                "Interior Designer",
                "Home Improvement",
                2000,
                "Professional interior design consultation for residential and small office spaces.",
            ),
            (
                "Tile Installation",
                "Home Improvement",
                50,
                "Floor and wall tile installation with proper alignment, grouting, and finishing (per sq.ft).",
            ),
            (
                "Wedding Photography",
                "Event Services",
                25000,
                "Professional wedding photography with candid coverage, album, and digital delivery.",
            ),
            (
                "Birthday Event Decorator",
                "Event Services",
                10000,
                "Birthday decoration including balloons, theme setup, backdrop, and basic lighting.",
            ),
            (
                "DJ & Sound Setup",
                "Event Services",
                8000,
                "DJ system with speakers, lighting, and event music coordination for parties and functions.",
            ),
            (
                "Babysitting Service",
                "Domestic Services",
                500,
                "Verified babysitters for child care and supervision at home (per hour).",
            ),
            (
                "Elder Care Service",
                "Health Services",
                1000,
                "Assistance for elderly individuals including basic medical support and companionship (per day).",
            ),
            (
                "Bridal Makeup Artist",
                "Beauty Services",
                12000,
                "Professional bridal makeup with hairstyling, draping, and complete wedding-day look.",
            ),
            (
                "Salon at Home",
                "Beauty Services",
                1200,
                "Haircut, facial, manicure, and basic grooming services at home.",
            ),
        ],
    }

    for email, svc_list in services_by_provider.items():
        provider_id = provider_ids.get(email)
        if not provider_id:
            continue
        for service_type, category, price, description in svc_list:
            cur = conn.execute(
                "SELECT id FROM services WHERE provider_id = ? AND service_type = ?",
                (provider_id, service_type),
            )
            if cur.fetchone():
                cur.close()
                continue
            cur.close()
            conn.execute(
                """
                INSERT INTO services (provider_id, service_type, category, price, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                (provider_id, service_type, category, price, description),
            )
            print(f"Seeded service '{service_type}' for provider {email}")


def main() -> None:
    os.makedirs(BASE_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(SCHEMA_SQL)

        seed_users_and_services(conn)

        conn.commit()
        print(f"DB path: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

