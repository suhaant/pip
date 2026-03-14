"""
Hack Island — Pump Agent Backend
FastAPI + Claude fleet-aware agentic reasoning with SSE streaming
"""
import json, os, uuid, csv
from datetime import datetime
from dotenv import load_dotenv
import anthropic
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pump_data import ALL_PUMPS, SCENARIOS, CSV_DIR

load_dotenv()
client = anthropic.Anthropic()
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

work_orders = []

# ── Startup check ─────────────────────────────────────────────────────────────
print(f"\n[startup] Looking for CSVs in: {CSV_DIR}")
for pump_id, pump in ALL_PUMPS.items():
    n = len(pump["sensor_readings"])
    status = "✓" if n > 0 else "✗ NO DATA"
    print(f"[startup]   {pump_id}: {n} readings {status}")
print()

# ── Tool implementations ──────────────────────────────────────────────────────

def get_fleet_status() -> dict:
    """Snapshot of all pumps — temp, pressure, flow, load, vibration, status."""
    fleet = []
    for pid, pump in ALL_PUMPS.items():
        readings = pump["sensor_readings"]
        if not readings:
            fleet.append({
                "pump_id": pid, "platform": pump["platform"],
                "status": pump["status"], "latest": None,
                "note": pump["operating_conditions"].get("note", "Offline"),
            })
            continue
        latest = readings[-1]
        first  = readings[0]
        fleet.append({
            "pump_id": pid,
            "platform": pump["platform"],
            "location": pump["location"],
            "status": pump["status"],
            "latest_temp_c": latest["temp_c"],
            "latest_pressure_bar": latest["pressure_bar"],
            "latest_flow_lpm": latest["flow_lpm"],
            "latest_load_pct": latest["load_pct"],
            "latest_vibration_mm_s": latest["vibration_mm_s"],
            "delta_temp_total": round(latest["temp_c"] - first["temp_c"], 1),
            "runtime_hours_since_service": pump["operating_conditions"].get("runtime_hours_since_service", "N/A"),
        })
    return {"fleet": fleet, "total_pumps": len(fleet),
            "alerts": [p for p in fleet if p["status"] in ("CRITICAL","HIGH","WARNING")]}

def get_pump_sensors(pump_id: str) -> dict:
    pump = ALL_PUMPS.get(pump_id)
    if not pump:
        return {"error": f"Pump {pump_id} not found"}
    return {
        "pump_id": pump["pump_id"], "location": pump["location"],
        "status": pump["status"],
        "readings": pump["sensor_readings"],
        "thresholds": pump.get("thresholds", {}),
        "reading_count": len(pump["sensor_readings"]),
        "latest": pump["sensor_readings"][-1] if pump["sensor_readings"] else None,
        "first": pump["sensor_readings"][0] if pump["sensor_readings"] else None,
    }

def get_pump_maintenance(pump_id: str) -> dict:
    pump = ALL_PUMPS.get(pump_id)
    if not pump:
        return {"error": f"Pump {pump_id} not found"}
    return {"pump_id": pump_id, "history": pump["maintenance_history"]}

def get_pump_parts(pump_id: str) -> dict:
    pump = ALL_PUMPS.get(pump_id)
    if not pump:
        return {"error": f"Pump {pump_id} not found"}
    inventory = pump.get("parts_inventory", {})
    if not inventory:
        return {"pump_id": pump_id, "note": "No parts data for this pump (healthy baseline)"}
    return {"pump_id": pump_id, "inventory": inventory}

def get_pump_conditions(pump_id: str) -> dict:
    pump = ALL_PUMPS.get(pump_id)
    if not pump:
        return {"error": f"Pump {pump_id} not found"}
    return {"pump_id": pump_id, "conditions": pump["operating_conditions"]}

def compare_pumps(pump_id_a: str, pump_id_b: str) -> dict:
    """Direct side-by-side comparison of two pumps — key for isolating root cause."""
    a = ALL_PUMPS.get(pump_id_a)
    b = ALL_PUMPS.get(pump_id_b)
    if not a or not b:
        return {"error": "One or both pumps not found"}
    def summary(p):
        if not p["sensor_readings"]:
            return {"status": p["status"], "note": "No readings"}
        latest = p["sensor_readings"][-1]
        first  = p["sensor_readings"][0]
        return {
            "pump_id": p["pump_id"], "platform": p["platform"],
            "status": p["status"],
            "latest_temp_c": latest["temp_c"],
            "latest_vibration_mm_s": latest["vibration_mm_s"],
            "latest_pressure_bar": latest["pressure_bar"],
            "latest_flow_lpm": latest["flow_lpm"],
            "latest_load_pct": latest["load_pct"],
            "delta_temp_total": round(latest["temp_c"] - first["temp_c"], 1),
            "runtime_hours_since_service": p["operating_conditions"].get("runtime_hours_since_service"),
        }
    sa, sb = summary(a), summary(b)
    return {
        "pump_a": sa, "pump_b": sb,
        "temp_difference_c": round(sa.get("latest_temp_c",0) - sb.get("latest_temp_c",0), 1),
        "vibration_difference_mm_s": round(sa.get("latest_vibration_mm_s",0) - sb.get("latest_vibration_mm_s",0), 2),
        "flow_difference_lpm": round(sa.get("latest_flow_lpm",0) - sb.get("latest_flow_lpm",0), 1),
        "same_platform": a["platform"] == b["platform"],
        "analysis_note": "Same platform pumps ruling out platform-level issues if one is nominal" if a["platform"] == b["platform"] else "Different platforms — ambient/shared system differences possible",
    }

def create_work_order(pump_id: str, severity: str, root_cause: str,
                      recommended_action: str, parts_required: list,
                      estimated_downtime_hours: float) -> dict:
    wo = {
        "work_order_id": f"WO-{uuid.uuid4().hex[:6].upper()}",
        "created_at": datetime.now().isoformat(),
        "pump_id": pump_id, "severity": severity,
        "root_cause": root_cause,
        "recommended_action": recommended_action,
        "parts_required": parts_required,
        "estimated_downtime_hours": estimated_downtime_hours,
        "status": "OPEN",
    }
    work_orders.append(wo)
    return {"success": True, "work_order": wo}

# ── Tool definitions ──────────────────────────────────────────────────────────
TOOL_DEFS = [
    {
        "name": "get_fleet_status",
        "description": "Get a live snapshot of ALL pumps in the fleet — temp, pressure, flow, load, vibration, status. ALWAYS call this first to scan the fleet and identify which pumps need attention.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_pump_sensors",
        "description": "Get full time-series sensor readings for a specific pump. Use after fleet scan to deep-dive an anomalous pump.",
        "input_schema": {
            "type": "object",
            "properties": {"pump_id": {"type": "string"}},
            "required": ["pump_id"]
        }
    },
    {
        "name": "compare_pumps",
        "description": "Side-by-side comparison of two pumps. Critical for isolating root cause — compare the suspect pump against a healthy pump running at similar load on the same or different platform.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pump_id_a": {"type": "string", "description": "The suspect pump"},
                "pump_id_b": {"type": "string", "description": "A healthy baseline pump for comparison"},
            },
            "required": ["pump_id_a", "pump_id_b"]
        }
    },
    {
        "name": "get_pump_maintenance",
        "description": "Get maintenance history for a pump. Look for recurring issues or time since last service.",
        "input_schema": {
            "type": "object",
            "properties": {"pump_id": {"type": "string"}},
            "required": ["pump_id"]
        }
    },
    {
        "name": "get_pump_parts",
        "description": "Check parts inventory for a specific pump. Only call after you have a diagnosis.",
        "input_schema": {
            "type": "object",
            "properties": {"pump_id": {"type": "string"}},
            "required": ["pump_id"]
        }
    },
    {
        "name": "get_pump_conditions",
        "description": "Get operating conditions — ambient temp, runtime hours, duty cycle, scheduled operations. Use to rule out false positives.",
        "input_schema": {
            "type": "object",
            "properties": {"pump_id": {"type": "string"}},
            "required": ["pump_id"]
        }
    },
    {
        "name": "create_work_order",
        "description": "Create a maintenance work order. ONLY call this if you have confirmed a real fault. Do NOT call for false positives.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pump_id": {"type": "string"},
                "severity": {"type": "string", "enum": ["LOW","MEDIUM","HIGH","CRITICAL"]},
                "root_cause": {"type": "string", "description": "Specific technical root cause with evidence"},
                "recommended_action": {"type": "string", "description": "Concrete step-by-step action for technician"},
                "parts_required": {"type": "array", "items": {"type": "string"}},
                "estimated_downtime_hours": {"type": "number"},
            },
            "required": ["pump_id","severity","root_cause","recommended_action","parts_required","estimated_downtime_hours"]
        }
    },
]

SYSTEM_PROMPT = """You are a pump fleet diagnostic agent. Be concise. No markdown tables, no headers, no bullet walls.

WORKFLOW:
1. get_fleet_status — find which pumps are alerting
2. get_pump_sensors — read the suspect pump's full trend
3. compare_pumps — compare suspect vs a healthy pump at similar load
4. get_pump_conditions — check for scheduled operations or high ambient temp
5. get_pump_maintenance — look for recurring issues or overdue service
6. get_pump_parts — check parts once you have a diagnosis
7. create_work_order if it's a real fault (not a false positive)
8. End with a short REPORT

DIAGNOSIS RULES:
- Temp up + vibration up + flow stable + load stable = bearing failure
- Temp up + pressure up + flow down + vibration stable = coolant blockage
- Temp spike tracks load% and returns to baseline = false positive, no work order
- Same platform, same load, one pump 30°C+ hotter = isolated pump fault, not environment

WRITING RULES — strictly follow these:
- Write in plain short sentences. Max 2 sentences per thought.
- Never use markdown tables or ### headers.
- When you have confirmed a detection, output exactly: DETECTION: [one sentence saying what pump has a problem and what the symptom is]
- When you have a diagnosis, output exactly: DIAGNOSIS: [one sentence naming the root cause and key evidence]
- Work order root_cause: one sentence. recommended_action: numbered steps, each under 10 words.

REPORT FORMAT (end every investigation with exactly this):
REPORT:
Pumps scanned: [X] — Alerts: [pump IDs and status]
Suspect: [pump ID] vs Baseline: [pump ID] — Temp gap: [X°C] at similar load
Root cause: [one sentence]
Severity: [NONE / LOW / MEDIUM / HIGH / CRITICAL]
Action: [work order ID, or "No action — false positive"]
Key evidence: [3 data points, comma separated]"""

def dispatch_tool(name: str, inputs: dict) -> str:
    if name == "get_fleet_status":
        return json.dumps(get_fleet_status())
    elif name == "get_pump_sensors":
        return json.dumps(get_pump_sensors(inputs["pump_id"]))
    elif name == "compare_pumps":
        return json.dumps(compare_pumps(inputs["pump_id_a"], inputs["pump_id_b"]))
    elif name == "get_pump_maintenance":
        return json.dumps(get_pump_maintenance(inputs["pump_id"]))
    elif name == "get_pump_parts":
        return json.dumps(get_pump_parts(inputs["pump_id"]))
    elif name == "get_pump_conditions":
        return json.dumps(get_pump_conditions(inputs["pump_id"]))
    elif name == "create_work_order":
        return json.dumps(create_work_order(**inputs))
    return json.dumps({"error": f"Unknown tool: {name}"})

# ── SSE Investigation Stream ──────────────────────────────────────────────────
@app.get("/investigate/{scenario}")
async def investigate(scenario: str):
    pump_data = SCENARIOS.get(scenario)
    if not pump_data:
        return {"error": "Unknown scenario"}

    async def stream():
        yield {"event": "start", "data": json.dumps({
            "scenario": scenario,
            "scenario_name": pump_data.get("scenario", scenario),
            "pump_id": pump_data["pump_id"],
            "fleet_size": len(ALL_PUMPS),
        })}

        messages = [{
            "role": "user",
            "content": "New overheating alert on the fleet. Scan all pumps, identify the anomaly, determine root cause, and take appropriate action."
        }]

        iteration = 0
        while iteration < 14:
            iteration += 1
            response = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=1800,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFS,
                messages=messages,
            )

            for block in response.content:
                if block.type == "text" and block.text.strip():
                    text = block.text.strip()
                    if text.startswith("REPORT:"):
                        yield {"event": "report", "data": json.dumps({"text": text})}
                    elif text.startswith("DETECTION:"):
                        yield {"event": "detection", "data": json.dumps({"text": text[10:].strip()})}
                    elif text.startswith("DIAGNOSIS:"):
                        yield {"event": "diagnosis", "data": json.dumps({"text": text[10:].strip()})}
                    else:
                        yield {"event": "thought", "data": json.dumps({"text": text})}
                elif block.type == "tool_use":
                    # Announce before create_work_order so UI can show "taking action"
                    if block.name == "create_work_order":
                        yield {"event": "pre_action", "data": json.dumps({
                            "pump_id": block.input.get("pump_id"),
                            "severity": block.input.get("severity"),
                            "action": block.input.get("recommended_action", ""),
                        })}
                    yield {"event": "tool_call", "data": json.dumps({
                        "tool": block.name, "input": block.input,
                    })}

            if response.stop_reason == "end_turn":
                break

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = dispatch_tool(block.name, dict(block.input))
                        result_data = json.loads(result)

                        if block.name == "create_work_order" and result_data.get("success"):
                            yield {"event": "work_order", "data": json.dumps(result_data["work_order"])}

                        yield {"event": "tool_result", "data": json.dumps({
                            "tool": block.name, "result": result_data,
                        })}
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

        yield {"event": "done", "data": json.dumps({"iterations": iteration})}

    return EventSourceResponse(stream())


@app.get("/export/work_orders")
def export_work_orders():
    """Download all work orders as CSV"""
    import io
    from fastapi.responses import StreamingResponse
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["work_order_id", "created_at", "pump_id", "severity",
                     "root_cause", "recommended_action", "estimated_downtime_hours", "status"])
    for wo in work_orders:
        writer.writerow([
            wo["work_order_id"], wo["created_at"], wo["pump_id"], wo["severity"],
            wo["root_cause"], wo["recommended_action"], wo["estimated_downtime_hours"], wo["status"]
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=work_orders.csv"}
    )


@app.get("/export/parts")
def export_parts():
    """Download parts requirements from all open work orders as CSV"""
    import io
    from fastapi.responses import StreamingResponse
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["work_order_id", "pump_id", "severity", "part_name",
                     "quantity_needed", "created_at"])
    for wo in work_orders:
        for part in wo.get("parts_required", []):
            writer.writerow([
                wo["work_order_id"], wo["pump_id"], wo["severity"],
                part, 1, wo["created_at"]
            ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=parts_required.csv"}
    )

@app.get("/fleet")
def fleet():
    return get_fleet_status()

@app.get("/work_orders")
def get_work_orders():
    return work_orders

@app.delete("/work_orders")
def clear_work_orders():
    work_orders.clear()
    return {"cleared": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)