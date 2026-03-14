import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "safety.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    return conn

def reset_db(cursor):
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

zones = ["Station_1", "Station_2", "Station_3", "Station_4"]
violation_types = ["no_hard_hat", "no_vest", "no_gloves", "no_goggles"]
worker_pool = [f"W{str(i).zfill(3)}" for i in range(100, 140)]
start_date = datetime(2026, 3, 4)
end_date = datetime(2026, 3, 11)

supervisors_default = {
    "Station_1": "Thompson",
    "Station_2": "Williams",
    "Station_3": "Johnson",
    "Station_4": "Davis",
}

# ── SCENARIO 1: Quota Pressure ──────────────────────────────────────────────
# Station 3 spikes March 7 — quota increases + new supervisor
def seed_quota_pressure():
    conn = get_conn()
    cursor = conn.cursor()
    reset_db(cursor)

    supervisors = {**supervisors_default, "Station_3_after": "Martinez"}
    violations = []
    current = start_date

    while current <= end_date:
        for zone in zones:
            num = random.randint(1, 3)
            if zone == "Station_3" and current >= datetime(2026, 3, 7):
                num = random.randint(8, 14)
            for _ in range(num):
                hour = random.randint(6, 18)
                ts = current.replace(hour=hour, minute=random.randint(0, 59))
                violations.append((ts.strftime("%Y-%m-%d %H:%M:%S"), zone,
                    random.choice(worker_pool), random.choice(violation_types),
                    round(random.uniform(0.75, 0.99), 2)))
        current += timedelta(days=1)

    cursor.executemany("INSERT INTO violations VALUES (NULL,?,?,?,?,?)", violations)

    shifts, quotas = [], []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        for zone in zones:
            for shift in ["morning", "night"]:
                sup = "Martinez" if (zone == "Station_3" and current >= datetime(2026, 3, 7)) else supervisors_default[zone]
                shifts.append((date_str, zone, sup, shift))
            target = 240 if (zone == "Station_3" and current >= datetime(2026, 3, 7)) else 200
            quotas.append((date_str, zone, target, int(target * random.uniform(0.85, 0.98))))
        current += timedelta(days=1)

    cursor.executemany("INSERT INTO shift_schedule VALUES (NULL,?,?,?,?)", shifts)
    cursor.executemany("INSERT INTO production_quotas VALUES (NULL,?,?,?,?)", quotas)
    conn.commit()
    conn.close()
    return "Scenario 1 loaded: Quota Pressure — Station 3 spike from quota increase + new supervisor"


# ── SCENARIO 2: New Hire ─────────────────────────────────────────────────────
# W042 starts March 7 at Station 2 — causes ~70% of that zone's violations
def seed_new_hire():
    conn = get_conn()
    cursor = conn.cursor()
    reset_db(cursor)

    NEW_HIRE = "W042"
    other_workers = [w for w in worker_pool if w != "W042"]
    violations = []
    current = start_date

    while current <= end_date:
        for zone in zones:
            for _ in range(random.randint(1, 3)):
                hour = random.randint(6, 18)
                ts = current.replace(hour=hour, minute=random.randint(0, 59))
                violations.append((ts.strftime("%Y-%m-%d %H:%M:%S"), zone,
                    random.choice(other_workers), random.choice(violation_types),
                    round(random.uniform(0.75, 0.99), 2)))

            if zone == "Station_2" and current >= datetime(2026, 3, 7):
                for _ in range(random.randint(4, 7)):
                    hour = random.randint(7, 17)
                    ts = current.replace(hour=hour, minute=random.randint(0, 59))
                    vtype = random.choices(violation_types, weights=[0.4, 0.35, 0.15, 0.1])[0]
                    violations.append((ts.strftime("%Y-%m-%d %H:%M:%S"), "Station_2",
                        NEW_HIRE, vtype, round(random.uniform(0.80, 0.99), 2)))
        current += timedelta(days=1)

    cursor.executemany("INSERT INTO violations VALUES (NULL,?,?,?,?,?)", violations)

    shifts, quotas = [], []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        for zone in zones:
            for shift in ["morning", "night"]:
                shifts.append((date_str, zone, supervisors_default[zone], shift))
            quotas.append((date_str, zone, 200, int(200 * random.uniform(0.90, 0.98))))
        current += timedelta(days=1)

    cursor.executemany("INSERT INTO shift_schedule VALUES (NULL,?,?,?,?)", shifts)
    cursor.executemany("INSERT INTO production_quotas VALUES (NULL,?,?,?,?)", quotas)
    conn.commit()
    conn.close()
    return "Scenario 2 loaded: New Hire — W042 causing 70% of Station 2 violations"


# ── SCENARIO 3: Night Shift Pattern ─────────────────────────────────────────
# Violations cluster on night shift across all zones — day shift is clean
def seed_night_shift():
    conn = get_conn()
    cursor = conn.cursor()
    reset_db(cursor)

    violations = []
    current = start_date

    while current <= end_date:
        for zone in zones:
            # Day shift (6am-6pm): 1-2 violations
            for _ in range(random.randint(1, 2)):
                hour = random.randint(6, 17)
                ts = current.replace(hour=hour, minute=random.randint(0, 59))
                violations.append((ts.strftime("%Y-%m-%d %H:%M:%S"), zone,
                    random.choice(worker_pool), random.choice(violation_types),
                    round(random.uniform(0.75, 0.92), 2)))

            # Night shift (6pm-6am): 6-10 violations
            for _ in range(random.randint(6, 10)):
                hour = random.randint(18, 23)
                ts = current.replace(hour=hour, minute=random.randint(0, 59))
                violations.append((ts.strftime("%Y-%m-%d %H:%M:%S"), zone,
                    random.choice(worker_pool), random.choice(violation_types),
                    round(random.uniform(0.75, 0.99), 2)))
        current += timedelta(days=1)

    cursor.executemany("INSERT INTO violations VALUES (NULL,?,?,?,?,?)", violations)

    # Night supervisors are different — less experienced
    night_supervisors = {
        "Station_1": "Kim",
        "Station_2": "Patel",
        "Station_3": "Chen",
        "Station_4": "Rivera",
    }

    shifts, quotas = [], []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        for zone in zones:
            shifts.append((date_str, zone, supervisors_default[zone], "morning"))
            shifts.append((date_str, zone, night_supervisors[zone], "night"))
            quotas.append((date_str, zone, 200, int(200 * random.uniform(0.88, 0.97))))
        current += timedelta(days=1)

    cursor.executemany("INSERT INTO shift_schedule VALUES (NULL,?,?,?,?)", shifts)
    cursor.executemany("INSERT INTO production_quotas VALUES (NULL,?,?,?,?)", quotas)
    conn.commit()
    conn.close()
    return "Scenario 3 loaded: Night Shift Pattern — violations 5x higher on night shift across all zones"


SCENARIOS = {
    "quota_pressure": seed_quota_pressure,
    "new_hire":       seed_new_hire,
    "night_shift":    seed_night_shift,
}

def load_scenario(name: str) -> str:
    if name not in SCENARIOS:
        return f"Unknown scenario: {name}"
    return SCENARIOS[name]()


if __name__ == "__main__":
    print(load_scenario("quota_pressure"))