# 🏭 Industrial AI Agents: Predictive Maintenance & HSE

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)
![Anthropic](https://img.shields.io/badge/AI-Claude_Opus-purple.svg)
![Vanilla JS](https://img.shields.io/badge/Frontend-Vanilla_JS-F7DF1E.svg)
![SQLite](https://img.shields.io/badge/DB-SQLite-003B57.svg)

This repository contains two enterprise-grade Proof-of-Concept (PoC) AI agents built using Anthropic's Claude framework. These autonomous agents are designed to revolutionize industrial facility operations across two critical domains: **Predictive Maintenance (Pump Intelligence)** and **Health, Safety & Environment (HSE)**.

By leveraging advanced tool-calling and continuous reasoning loops, these agents move beyond simple chatbots to act as autonomous facility operators capable of cross-referencing telemetry, querying databases, and executing preventative actions.

---

## 📑 Table of Contents

1. [Architecture Overview](#-architecture-overview)
2. [Project 1: Pump Intelligence Platform (Predictive Maintenance)](#1-pump-intelligence-platform-predictive-maintenance)
3. [Project 2: Autonomous Safety Manager (HSE)](#2-autonomous-safety-manager-hse)
4. [Installation & Setup](#-installation--setup)
5. [Usage & Simulation](#-usage--simulation)
6. [Repository Structure](#-repository-structure)

---

## 🏗 Architecture Overview

This repository is split into two distinct agentic systems:

1. **The Reactive / Diagnostic Agent (Pump Intelligence):** A FastAPI-driven agent that receives real-time telemetry alerts, actively queries a fleet state, isolates mechanical faults by comparing peer baselines, and issues automated work orders. Its thought process is streamed live to a dynamic web UI via Server-Sent Events (SSE).
2. **The Proactive / Continuous Agent (Safety Manager):** A CLI-based agent operating in a continuous loop. It queries a local SQLite database for safety violations, correlates them against shift schedules and production quotas, and proactively flags systemic risks before accidents occur.

---

## 1. Pump Intelligence Platform (Predictive Maintenance)

A comprehensive web dashboard and backend system simulating a fleet of 7 industrial pumps. 

### ✨ Key Features
* **Live Telemetry Dashboard:** Visualizes Temperature, Pressure, Flow Rate, Load %, and Vibration using a custom SVG charting engine and CSS gauges.
* **Agentic Root Cause Analysis:** The Claude agent utilizes 7 distinct tools to diagnose issues:
  * `get_fleet_status`: Scans the entire fleet for alerts.
  * `get_pump_sensors`: Extracts time-series data.
  * `compare_pumps`: Compares a suspect pump against a healthy baseline to rule out environmental factors.
  * `get_pump_maintenance` & `get_pump_parts`: Checks service history and inventory.
  * `get_pump_conditions`: Analyzes ambient temperature and duty cycles.
* **Automated Directives:** Upon confirming a fault (and ruling out false positives), the agent executes `create_work_order`, triggering a downloadable CSV export for maintenance technicians and parts requests.
* **Streaming Transparency:** The agent's thought process (`thought`, `tool_call`, `data`, `report`) is streamed in real-time to the "Memory Trace" UI panel via SSE.

---

## 2. Autonomous Safety Manager (HSE)

An autonomous CLI agent designed to act as a 24/7 safety manager. It minimizes injury risk by continuously analyzing a simulated database of worker violations.

### ✨ Key Features
* **Continuous Monitoring:** Runs on a continuous 5-minute cron-style loop, querying the database without human prompting.
* **Multi-Variate Correlation:** The agent correlates data across three SQLite tables: `violations`, `shift_schedule`, and `production_quotas`.
* **SQL Tool Integration:** Equipped with specific tools to slice data:
  * `get_recent_violations`
  * `get_shift_schedule`
  * `get_production_quotas`
  * `send_recommendation`
* **Automated Escalation:** When a root cause is identified (e.g., a specific new hire, quota pressure, or a tired night shift), the agent generates a specific recommendation and logs it to `recommendations.txt`.

### 🎭 Built-in Scenarios
The database can be seeded with three specific safety narratives:
1. **Quota Pressure:** A sudden spike in violations at Station 3 driven by an increase in production targets and a new supervisor.
2. **New Hire:** Worker `W042` starts on March 7th and is responsible for ~70% of PPE violations at Station 2.
3. **Night Shift Fatigue:** Violations cluster heavily during night shifts across all zones, while day shifts remain clean.

---

## 🚀 Installation & Setup

### Prerequisites
* Python 3.8+
* Anthropic API Key (Claude 3 Opus/Sonnet)

### 1. Clone & Environment Setup
```bash
git clone [https://github.com/your-username/industrial-ai-agents.git](https://github.com/your-username/industrial-ai-agents.git)
cd industrial-ai-agents

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install fastapi uvicorn anthropic python-dotenv sse-starlette

```

### 2. Configure Environment Variables

Create a `.env` file in the root directory for the FastAPI backend:

```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

```

*Note: For the Safety Agent, you must also insert your API key directly into `agent.py` at `API_KEY = "xxx"`.*

---

## 💻 Usage & Simulation

### Starting the Predictive Maintenance Platform

1. Start the FastAPI backend server:
```bash
python backend.py

```


*The server will start on `http://0.0.0.0:8000`.*
2. Open `dashboard.html` in your web browser.
3. **Run a Scenario:** Use the top navigation bar to inject a fault (e.g., *Bearing Failure*, *Coolant Blockage*, or *False Positive*), then click **Initialize Agent** to watch the AI diagnose the system live.

### Starting the Autonomous Safety Manager

1. First, seed the SQLite database (`safety.db`) with a scenario:
```bash
# Seeds the default 'New Hire' W042 scenario
python seed_db.py 

```


*(Alternatively, modify `scenarios.py` to test quota pressure or night shift patterns).*
2. Start the continuous agent loop:
```bash
python agent.py

```


3. Watch the terminal as the agent queries the database, forms hypotheses, and outputs recommendations. Check `recommendations.txt` for the final alerts.

---
```

```
