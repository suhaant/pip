"""
Hack Island — Pump Data
Sensor readings are loaded from CSV files at runtime.

To change sensor data, edit the CSV files directly:
  PUMP-02_sensors.csv  (healthy baseline, Platform B)
  PUMP-03_sensors.csv  (false positive scenario, Platform C)
  PUMP-04_sensors.csv  (healthy baseline, Platform C)
  PUMP-07_sensors.csv  (bearing failure scenario, Platform B)
  PUMP-09_sensors.csv  (healthy baseline, Platform A)
  PUMP-12_sensors.csv  (coolant blockage scenario, Platform A)

CSV columns: timestamp, temp_c, pressure_bar, flow_lpm, load_pct, vibration_mm_s, delta_temp
"""
import csv, os

CSV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pump_files")

def load_csv(pump_id: str) -> list:
    # Support both "PUMP-07_sensors.csv" and "Pump07.csv" naming
    short_id = pump_id.replace("PUMP-", "Pump")  # PUMP-07 → Pump07
    candidates = [
        os.path.join(CSV_DIR, f"{pump_id}_sensors.csv"),  # PUMP-07_sensors.csv
        os.path.join(CSV_DIR, f"{short_id}.csv"),          # Pump07.csv
        os.path.join(CSV_DIR, f"{pump_id}.csv"),           # PUMP-07.csv
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        print(f"[pump_data] WARNING: No CSV found for {pump_id}. Tried: {candidates}")
        return []
    rows = []
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            rows.append({
                "timestamp":      row["timestamp"],
                "temp_c":         float(row["temp_c"]),
                "pressure_bar":   float(row["pressure_bar"]),
                "flow_lpm":       float(row["flow_lpm"]),
                "load_pct":       float(row["load_pct"]),
                "vibration_mm_s": float(row["vibration_mm_s"]),
                "delta_temp":     float(row["delta_temp"]),
            })
    return rows

# ── Healthy baseline pumps ────────────────────────────────────────────────────

PUMP_02 = {
    "pump_id": "PUMP-02", "platform": "Platform B",
    "location": "Platform B — Injection Line", "status": "NOMINAL",
    "sensor_readings": load_csv("PUMP-02"),
    "maintenance_history": [
        {"date": "2025-01-10", "type": "Scheduled PM", "notes": "All nominal, bearings excellent"},
        {"date": "2024-08-22", "type": "Scheduled PM", "notes": "Minor seal replaced, otherwise clean"},
    ],
    "operating_conditions": {
        "ambient_temp_c": 31, "runtime_hours_since_service": 1240,
        "duty_cycle_pct": 85, "rated_max_temp_c": 105,
    }
}

PUMP_04 = {
    "pump_id": "PUMP-04", "platform": "Platform C",
    "location": "Platform C — Primary Injection", "status": "NOMINAL",
    "sensor_readings": load_csv("PUMP-04"),
    "maintenance_history": [
        {"date": "2025-03-01", "type": "Scheduled PM", "notes": "Recent full service, excellent condition"},
        {"date": "2024-11-20", "type": "Scheduled PM", "notes": "All nominal"},
    ],
    "operating_conditions": {
        "ambient_temp_c": 29, "runtime_hours_since_service": 320,
        "duty_cycle_pct": 75, "rated_max_temp_c": 105,
        "high_load_operation_scheduled": True,
        "high_load_window": "06:00–08:00 local — planned surge injection",
    }
}

PUMP_09 = {
    "pump_id": "PUMP-09", "platform": "Platform A",
    "location": "Platform A — Transfer Line", "status": "NOMINAL",
    "sensor_readings": load_csv("PUMP-09"),
    "maintenance_history": [
        {"date": "2025-02-01", "type": "Scheduled PM", "notes": "Full coolant flush, new filter, all clean"},
        {"date": "2024-09-14", "type": "Scheduled PM", "notes": "All nominal"},
    ],
    "operating_conditions": {
        "ambient_temp_c": 33, "runtime_hours_since_service": 780,
        "duty_cycle_pct": 80, "rated_max_temp_c": 105,
    }
}

PUMP_11 = {
    "pump_id": "PUMP-11", "platform": "Platform B",
    "location": "Platform B — Secondary Line", "status": "OFFLINE",
    "sensor_readings": [],  # Offline — no CSV data
    "maintenance_history": [
        {"date": "2025-03-10", "type": "Scheduled Overhaul", "notes": "Offline for planned impeller replacement — ETA 2 days"},
    ],
    "operating_conditions": {
        "ambient_temp_c": 31, "runtime_hours_since_service": 0,
        "duty_cycle_pct": 0, "rated_max_temp_c": 105,
        "note": "Offline — planned maintenance",
    }
}

# ── Scenario pumps ────────────────────────────────────────────────────────────

PUMP_07 = {
    "pump_id": "PUMP-07", "platform": "Platform B",
    "location": "Platform B — Injection Line", "status": "CRITICAL",
    "scenario": "bearing_failure",
    "scenario_description": "Progressive bearing degradation. Temp and vibration rising over 4 hours despite normal load.",
    "sensor_readings": load_csv("PUMP-07"),
    "thresholds": {"temp_warning": 85, "temp_critical": 105, "vibration_warning": 5.0, "vibration_critical": 10.0},
    "maintenance_history": [
        {"date": "2024-09-15", "type": "Scheduled PM", "notes": "Bearing lubrication, normal wear"},
        {"date": "2024-06-02", "type": "Bearing Replacement", "notes": "Replaced rear bearing set — 14 months service"},
        {"date": "2024-01-10", "type": "Scheduled PM", "notes": "All readings nominal"},
    ],
    "parts_inventory": {
        "bearing_set_type_b7": {"in_stock": True,  "quantity": 2, "location": "Warehouse B, Shelf 3"},
        "shaft_seal_kit":      {"in_stock": True,  "quantity": 4, "location": "Warehouse B, Shelf 1"},
        "impeller_assembly":   {"in_stock": False, "quantity": 0, "lead_time_days": 5},
        "motor_coupling":      {"in_stock": True,  "quantity": 1, "location": "Warehouse A, Shelf 7"},
    },
    "operating_conditions": {
        "ambient_temp_c": 31, "runtime_hours_since_service": 4380,
        "duty_cycle_pct": 88, "rated_max_temp_c": 105, "rated_max_vibration_mm_s": 10.0,
    }
}

PUMP_12 = {
    "pump_id": "PUMP-12", "platform": "Platform A",
    "location": "Platform A — Transfer Line", "status": "HIGH",
    "scenario": "coolant_blockage",
    "scenario_description": "Suspected partial blockage in cooling circuit. Pressure building, flow dropping, temp escalating rapidly.",
    "sensor_readings": load_csv("PUMP-12"),
    "thresholds": {"temp_warning": 85, "temp_critical": 105, "pressure_warning": 22.0, "pressure_critical": 27.0, "flow_warning": 220},
    "maintenance_history": [
        {"date": "2025-01-28", "type": "Filter Inspection", "notes": "Coolant filter at 70% — flagged for next PM"},
        {"date": "2024-11-05", "type": "Scheduled PM", "notes": "Full coolant flush, new filter"},
        {"date": "2024-07-19", "type": "Unplanned — Overtemp", "notes": "Scale buildup in cooling line, cleaned"},
    ],
    "parts_inventory": {
        "coolant_filter_12in":   {"in_stock": True,  "quantity": 6, "location": "Warehouse A, Shelf 2"},
        "descaling_kit":         {"in_stock": True,  "quantity": 3, "location": "Warehouse A, Shelf 4"},
        "cooling_hose_assembly": {"in_stock": False, "quantity": 0, "lead_time_days": 3},
        "temp_sensor_probe":     {"in_stock": True,  "quantity": 5, "location": "Warehouse B, Shelf 6"},
    },
    "operating_conditions": {
        "ambient_temp_c": 33, "runtime_hours_since_service": 1850,
        "duty_cycle_pct": 82, "rated_max_temp_c": 105, "rated_max_pressure_bar": 27.0,
    }
}

PUMP_03 = {
    "pump_id": "PUMP-03", "platform": "Platform C",
    "location": "Platform C — Primary Injection", "status": "WARNING",
    "scenario": "false_positive",
    "scenario_description": "Temp briefly exceeded warning threshold during planned peak-load surge. All other readings nominal.",
    "sensor_readings": load_csv("PUMP-03"),
    "thresholds": {"temp_warning": 85, "temp_critical": 105},
    "maintenance_history": [
        {"date": "2025-02-20", "type": "Scheduled PM", "notes": "Full inspection — all systems nominal, bearings excellent"},
        {"date": "2024-10-11", "type": "Scheduled PM", "notes": "Minor seal replacement, otherwise clean"},
    ],
    "parts_inventory": {
        "bearing_set_type_b7": {"in_stock": True, "quantity": 2, "location": "Warehouse B, Shelf 3"},
        "shaft_seal_kit":      {"in_stock": True, "quantity": 4, "location": "Warehouse B, Shelf 1"},
    },
    "operating_conditions": {
        "ambient_temp_c": 29, "runtime_hours_since_service": 620,
        "duty_cycle_pct": 78, "rated_max_temp_c": 105,
        "high_load_operation_scheduled": True,
        "high_load_window": "06:00–08:00 local — planned surge injection",
    }
}

# ── Fleet registry ────────────────────────────────────────────────────────────
ALL_PUMPS = {
    "PUMP-02": PUMP_02,
    "PUMP-03": PUMP_03,
    "PUMP-04": PUMP_04,
    "PUMP-07": PUMP_07,
    "PUMP-09": PUMP_09,
    "PUMP-11": PUMP_11,
    "PUMP-12": PUMP_12,
}

SCENARIOS = {
    "bearing_failure":  PUMP_07,
    "coolant_blockage": PUMP_12,
    "false_positive":   PUMP_03,
}