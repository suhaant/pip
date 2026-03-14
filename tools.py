import sqlite3
from datetime import datetime

DB_PATH = "safety.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- Tool 1: Get recent violations ---
def get_recent_violations(zone: str = "all", time_range_days: int = 7) -> list[dict]:
    """
    Returns violation events filtered by zone and time range.
    zone: specific zone name or "all"
    time_range_days: how many days back to look
    """
    conn = get_db()
    cursor = conn.cursor()

    cutoff = datetime.now().strftime("%Y-%m-%d")

    if zone == "all":
        cursor.execute("""
            SELECT zone, worker_id, violation_type, confidence, timestamp
            FROM violations
            WHERE date(timestamp) >= date(?, ?)
            ORDER BY timestamp DESC
        """, (cutoff, f"-{time_range_days} days"))
    else:
        cursor.execute("""
            SELECT zone, worker_id, violation_type, confidence, timestamp
            FROM violations
            WHERE zone = ? AND date(timestamp) >= date(?, ?)
            ORDER BY timestamp DESC
        """, (zone, cutoff, f"-{time_range_days} days"))

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


# --- Tool 2: Get shift schedule ---
def get_shift_schedule(zone: str = "all", date_range_days: int = 7) -> list[dict]:
    """
    Returns shift schedule filtered by zone and date range.
    zone: specific zone name or "all"
    date_range_days: how many days back to look
    """
    conn = get_db()
    cursor = conn.cursor()

    cutoff = datetime.now().strftime("%Y-%m-%d")

    if zone == "all":
        cursor.execute("""
            SELECT date, zone, supervisor, shift
            FROM shift_schedule
            WHERE date >= date(?, ?)
            ORDER BY date DESC
        """, (cutoff, f"-{date_range_days} days"))
    else:
        cursor.execute("""
            SELECT date, zone, supervisor, shift
            FROM shift_schedule
            WHERE zone = ? AND date >= date(?, ?)
            ORDER BY date DESC
        """, (zone, cutoff, f"-{date_range_days} days"))

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


# --- Tool 3: Get production quotas ---
def get_production_quotas(zone: str = "all", date_range_days: int = 7) -> list[dict]:
    """
    Returns production quota data filtered by zone and date range.
    zone: specific zone name or "all"
    date_range_days: how many days back to look
    """
    conn = get_db()
    cursor = conn.cursor()

    cutoff = datetime.now().strftime("%Y-%m-%d")

    if zone == "all":
        cursor.execute("""
            SELECT date, zone, target_units, actual_units
            FROM production_quotas
            WHERE date >= date(?, ?)
            ORDER BY date DESC
        """, (cutoff, f"-{date_range_days} days"))
    else:
        cursor.execute("""
            SELECT date, zone, target_units, actual_units
            FROM production_quotas
            WHERE zone = ? AND date >= date(?, ?)
            ORDER BY date DESC
        """, (zone, cutoff, f"-{date_range_days} days"))

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


# --- Tool 4: Send recommendation ---
def send_recommendation(target: str, message: str) -> dict:
    """
    Sends a recommendation to a supervisor or manager.
    In production this would send an email/Slack message.
    For demo purposes, logs to recommendations.txt.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] TO: {target}\n{message}\n{'-'*50}\n"

    with open("recommendations.txt", "a") as f:
        f.write(entry)

    print(f"\n📨 Recommendation sent to {target}:\n{message}\n")

    return {"status": "sent", "target": target, "timestamp": timestamp}


# --- Tool definitions for Claude API ---
TOOL_DEFINITIONS = [
    {
        "name": "get_recent_violations",
        "description": "Query safety violation events from the database. Use this to check violation frequency, types, and which zones are most affected.",
        "input_schema": {
            "type": "object",
            "properties": {
                "zone": {
                    "type": "string",
                    "description": "Zone to query. Use 'all' for all zones or a specific zone like 'Station_3'."
                },
                "time_range_days": {
                    "type": "integer",
                    "description": "How many days back to look. Default is 7."
                }
            },
            "required": ["zone"]
        }
    },
    {
        "name": "get_shift_schedule",
        "description": "Query shift schedules to see which supervisors are assigned to which zones and when. Use this to correlate safety events with staffing changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "zone": {
                    "type": "string",
                    "description": "Zone to query. Use 'all' for all zones or a specific zone like 'Station_3'."
                },
                "date_range_days": {
                    "type": "integer",
                    "description": "How many days back to look. Default is 7."
                }
            },
            "required": ["zone"]
        }
    },
    {
        "name": "get_production_quotas",
        "description": "Query production quota data to see if output targets have changed. Use this to correlate safety events with production pressure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "zone": {
                    "type": "string",
                    "description": "Zone to query. Use 'all' for all zones or a specific zone like 'Station_3'."
                },
                "date_range_days": {
                    "type": "integer",
                    "description": "How many days back to look. Default of 7."
                }
            },
            "required": ["zone"]
        }
    },
    {
        "name": "send_recommendation",
        "description": "Send a recommendation or alert to a supervisor or manager. Use this when you have identified an actionable insight or escalation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Who to send the recommendation to, e.g. 'Floor Manager' or 'Safety Officer'."
                },
                "message": {
                    "type": "string",
                    "description": "The recommendation message. Be specific about the problem, root cause, and suggested action."
                }
            },
            "required": ["target", "message"]
        }
    }
]

# --- Tool dispatcher ---
def dispatch_tool(tool_name: str, tool_input: dict):
    if tool_name == "get_recent_violations":
        return get_recent_violations(**tool_input)
    elif tool_name == "get_shift_schedule":
        return get_shift_schedule(**tool_input)
    elif tool_name == "get_production_quotas":
        return get_production_quotas(**tool_input)
    elif tool_name == "send_recommendation":
        return send_recommendation(**tool_input)
    else:
        return {"error": f"Unknown tool: {tool_name}"}