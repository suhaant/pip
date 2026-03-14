import sqlite3
import random
from datetime import datetime, timedelta

conn = sqlite3.connect("safety.db")
cursor = conn.cursor()

cursor.executescript("""
    DROP TABLE IF EXISTS violations;
    DROP TABLE IF EXISTS shift_schedule;
    DROP TABLE IF EXISTS production_quotas;

    CREATE TABLE violations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        zone TEXT,
        worker_id TEXT,
        violation_type TEXT,
        confidence REAL
    );

    CREATE TABLE shift_schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        zone TEXT,
        supervisor TEXT,
        shift TEXT
    );

    CREATE TABLE production_quotas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        zone TEXT,
        target_units INTEGER,
        actual_units INTEGER
    );
""")

# --- Narrative ---
# W042 is a new hire who started March 7 at Station_2
# W042 accounts for ~70% of Station_2 violations
# All other zones have normal baseline violations
# No quota changes, no supervisor changes
# The agent should identify W042 as the root cause

NEW_HIRE = "W042"
NEW_HIRE_START = datetime(2026, 3, 7)

zones = ["Station_1", "Station_2", "Station_3", "Station_4"]
violation_types = ["no_hard_hat", "no_vest", "no_gloves", "no_goggles"]
worker_pool = [f"W{str(i).zfill(3)}" for i in range(100, 140) if i != 42]

supervisors = {
    "Station_1": "Thompson",
    "Station_2": "Williams",
    "Station_3": "Johnson",
    "Station_4": "Davis",
}

start_date = datetime(2026, 3, 4)
end_date = datetime(2026, 3, 11)

# --- Seed violations ---
violations = []
current = start_date

while current <= end_date:
    for zone in zones:
        # Baseline: 1-3 violations per zone from regular workers
        num_baseline = random.randint(1, 3)
        for _ in range(num_baseline):
            hour = random.randint(6, 18)
            minute = random.randint(0, 59)
            ts = current.replace(hour=hour, minute=minute)
            violations.append((
                ts.strftime("%Y-%m-%d %H:%M:%S"),
                zone,
                random.choice(worker_pool),
                random.choice(violation_types),
                round(random.uniform(0.75, 0.99), 2)
            ))

        # W042 starts March 7, assigned to Station_2
        # Commits 4-7 violations per day — consistently missing PPE
        if zone == "Station_2" and current >= NEW_HIRE_START:
            num_new_hire = random.randint(4, 7)
            for _ in range(num_new_hire):
                hour = random.randint(7, 17)
                minute = random.randint(0, 59)
                ts = current.replace(hour=hour, minute=minute)
                # New hire most commonly forgets hard hat and vest
                vtype = random.choices(
                    violation_types,
                    weights=[0.4, 0.35, 0.15, 0.1]
                )[0]
                violations.append((
                    ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "Station_2",
                    NEW_HIRE,
                    vtype,
                    round(random.uniform(0.80, 0.99), 2)
                ))

    current += timedelta(days=1)

cursor.executemany(
    "INSERT INTO violations (timestamp, zone, worker_id, violation_type, confidence) VALUES (?, ?, ?, ?, ?)",
    violations
)

# --- Seed shift schedule (stable — no supervisor changes) ---
shifts = []
current = start_date

while current <= end_date:
    date_str = current.strftime("%Y-%m-%d")
    for zone in zones:
        for shift in ["morning", "night"]:
            shifts.append((date_str, zone, supervisors[zone], shift))
    current += timedelta(days=1)

cursor.executemany(
    "INSERT INTO shift_schedule (date, zone, supervisor, shift) VALUES (?, ?, ?, ?)",
    shifts
)

# --- Seed production quotas (stable — no changes) ---
quotas = []
current = start_date

while current <= end_date:
    date_str = current.strftime("%Y-%m-%d")
    for zone in zones:
        target = 200
        actual = int(target * random.uniform(0.90, 0.98))
        quotas.append((date_str, zone, target, actual))
    current += timedelta(days=1)

cursor.executemany(
    "INSERT INTO production_quotas (date, zone, target_units, actual_units) VALUES (?, ?, ?, ?)",
    quotas
)

conn.commit()
conn.close()

print("Database seeded successfully.")
print("Narrative: W042 (new hire) started March 7 at Station_2 — accounts for ~70% of Station_2 violations.")
print("No quota changes, no supervisor changes. Agent should identify W042 as root cause.")