# Digital System for Procurement Schedules, Farmer Queues and Real-Time Procurement Status

**Smart India Hackathon 2026 — Problem Statement PS ID: 26032**  
**Theme:** Agriculture, Food Security & Rural Development  
**Target Solution:** Production-grade full-stack procurement platform eliminating farmer wait uncertainty through digital tokens, algorithmic queue optimization, and live real-time status feeds.

---

## 1. Executive Summary & Architecture

This platform provides an end-to-end digital lifecycle for agricultural procurement under the Minimum Support Price (MSP) program. It interconnects five core technologies with distinct, meaningful responsibilities:

```
                                  [ WEB CLIENT (HTML5/CSS3/Vanilla JS) ]
                              Tri-Lingual: English (en), Hindi (hi), Telugu (te)
                                 Rural-Optimized (Zero Heavy NPM Bundles)
                                            │                 ▲
                                  REST APIs │                 │ WebSockets (/ws/live)
                                            ▼                 │
                       ┌─────────────────────────────────────────────────────────┐
                       │               FASTAPI BACKEND (Python 3.9+)             │
                       │ - Async REST API Endpoints & Role-Based Access Control   │
                       │ - Real-Time Pub/Sub Room Broadcast Engine               │
                       │ - ctypes Foreign Function Interface (FFI) Native Bridge  │
                       └─────────────┬───────────────────────────┬───────────────┘
                                     │                           │
                    Native ctypes    │                           │ Native ctypes
                    Sub-microsecond  │                           │ Sub-millisecond
                                     ▼                           ▼
      ┌─────────────────────────────────────────┐     ┌─────────────────────────────────────────┐
      │         C ACCELERATION ENGINE           │     │          C++ OPTIMIZATION ENGINE        │
      │       `c_modules/libcqueue.dylib`       │     │     `cpp_modules/libcppqueue_opt.dylib` │
      │ - Token Generation with CRC8 Checksum   │     │ - Center Workload & Counter Optimizer   │
      │ - Waiting-Time EWMA Formula Calculation │     │ - Fairness & Aging-Aware Prioritization │
      │ - Rapid O(1) Queue Ahead & ETA Solver   │     │ - Stochastic Discrete-Event Simulator   │
      └─────────────────────────────────────────┘     └─────────────────────────────────────────┘
                                     │
                                     │ SQL Queries, Indexes, & Analytical Views
                                     ▼
                       ┌─────────────────────────────────────────────────────────┐
                       │                 POSTGRESQL 16 DATABASE                  │
                       │ - 16 Relational Tables with Foreign Keys & Constraints   │
                       │ - 3 Real-time Analytical Reporting Views                │
                       │ - Composite B-Tree Indexes for High-Throughput Mandis   │
                       └─────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack & Role Interaction

| Technology | Implementation Scope & Meaningful Usage |
| :--- | :--- |
| **Python** | FastAPI async application core, JWT role-based authentication, WebSocket connection manager for live client dispatch, ORM schema mapping, and `ctypes` foreign function orchestration. |
| **C** | High-performance compiled shared library (`libcqueue`). Executes O(1) queue position solvers, calculates Exponentially Weighted Moving Average (EWMA) waiting times, formats alphanumeric tokens (e.g., `A023`), and computes CRC8 verification tags. |
| **C++** | High-throughput optimization engine (`libcppqueue_opt`). Implements priority queue fairness balancing (`std::priority_queue`), center workload capacity leveling, bottleneck hour detection, and discrete-event stochastic simulations (`<random>`). |
| **SQL** | Normalized PostgreSQL scripts (`database/schema.sql`, `seed.sql`, `queries.sql`). Advanced joins, group-by aggregations, window functions, and real-time views (`v_live_center_queue_status`, `v_farmer_turn_tracker`, `v_procurement_center_analytics`). |
| **PostgreSQL** | Primary running database engine (PostgreSQL 16) storing all users, procurement centers, commodities, time slots, digital tokens, weighbridge transactions, and audit logs. |
| **Frontend** | Pure HTML5, Vanilla CSS3, Vanilla JavaScript. Zero heavy NPM runtime dependencies for fast rendering on 2G/3G rural networks. Web Audio API synthesized alert tones. Multi-language (English, Hindi, Telugu). |

---

## 3. Project Directory Structure

```
katPro/
├── c_modules/                      # C Performance Acceleration Engine
│   ├── queue_fast.h                # C Header & Struct Definitions
│   ├── queue_fast.c                # Token Generator, CRC8, EWMA Wait-Time Formula
│   └── Makefile                    # Builds libcqueue.dylib / libcqueue.so
│
├── cpp_modules/                    # C++ Advanced Queue Optimizer & Simulation
│   ├── optimizer.h                 # C++ Header & C-ABI Declarations
│   ├── optimizer.cpp               # Workload Analysis, Priority Queue, Monte Carlo Sim
│   └── Makefile                    # Builds libcppqueue_opt.dylib / libcppqueue_opt.so
│
├── database/                       # PostgreSQL Database Layer
│   ├── schema.sql                  # 16 Relational Tables, Constraints, Indexes, Views
│   ├── seed.sql                    # Realistic Seed: 22 Farmers, 4 Centers, Active Queues
│   └── queries.sql                 # SIH Reporting & Analytical SQL Queries
│
├── backend/                        # Python FastAPI Backend
│   └── app/
│       ├── main.py                 # App Entrypoint, CORS, WebSockets, Lifespan
│       ├── config.py               # Env Configuration, DB URL, Library Paths
│       ├── database.py             # PostgreSQL Engine, SessionLocal, Auto-Migration
│       ├── models.py               # SQLAlchemy ORM Models
│       ├── schemas.py              # Pydantic v2 Request/Response Schemas
│       ├── auth.py                 # bcrypt Password Hashing & JWT RBAC
│       ├── c_bridge.py             # ctypes Wrapper for libcqueue
│       ├── cpp_bridge.py           # ctypes Wrapper for libcppqueue_opt
│       ├── websocket_manager.py    # Room & User WebSocket Broadcast Engine
│       └── routes/
│           ├── auth_routes.py      # Registration, Login, Demo Access
│           ├── farmer_routes.py    # Booking Wizard, Live Token, History, Alerts
│           ├── official_routes.py  # Call Next, Complete Transaction, Skip, Status
│           ├── admin_routes.py     # State KPIs, Center Management, C++ Runner
│           └── public_routes.py    # Public Feeds, Health Check Telemetry
│
├── frontend/                       # Rural-Friendly Web UI (No Bundler Needed)
│   ├── index.html                  # Portal Home, Demo Access, Public Status Ticker
│   ├── farmer.html                 # Farmer Dashboard, Live Status Card, QR Pass
│   ├── official.html               # Center Official Control Console
│   ├── admin.html                  # State Analytics, SVG Charts, C++ Optimizer UI
│   ├── css/
│   │   └── style.css               # Agricultural Gov Design System (Green/Saffron)
│   └── js/
│       ├── i18n.js                 # English, Hindi, Telugu Localization Engine
│       ├── app.js                  # Shared API Client, Web Audio Synthesizer, WebSocket
│       ├── farmer.js               # Farmer Controller & SVG QR Pass Generator
│       ├── official.js             # Official Controller & Live Queue Management
│       └── admin.js                # Administrator Controller & Pure SVG Charts
│
├── tests/                          # Automated Pytest Suite (16 Test Cases)
│   ├── test_c_module.py            # Validates C Token & Queue Calculations
│   ├── test_cpp_module.py          # Validates C++ Workload Optimizer & Simulation
│   ├── test_api_auth.py            # Tests Health, JWT, and RBAC Protections
│   ├── test_queue_workflow.py      # Full Lifecycle: Book -> Call -> Weigh -> Complete
│   └── test_db_queries.py          # Executes PostgreSQL Views & Aggregations
│
├── requirements.txt                # Python Dependencies
├── run_demo.sh                     # Automated Setup & Execution Script
├── Dockerfile                      # Container Build File
├── docker-compose.yml              # Multi-Container Compose Setup (App + DB)
└── README.md                       # Comprehensive Documentation
```

---

## 4. Setup & Installation Instructions

### Prerequisites
- macOS or Linux
- Python 3.9+
- Clang / Clang++ or GCC / G++ (`make`)
- PostgreSQL 16

### Quick Launch (One-Command)
```bash
./run_demo.sh
```
This script automatically:
1. Starts the PostgreSQL 16 server
2. Recompiles the C acceleration library (`libcqueue.dylib`)
3. Recompiles the C++ optimization library (`libcppqueue_opt.dylib`)
4. Applies `database/schema.sql` and `database/seed.sql`
5. Launches the Uvicorn web server at `http://localhost:8000`

---

### Manual Step-by-Step Setup

#### Step 1: PostgreSQL Setup
```bash
# Ensure PostgreSQL is running
pg_ctl -D /opt/homebrew/var/postgresql@16 start

# Create database
createdb sih_procurement

# Apply schema and realistic seed data
psql -d sih_procurement -f database/schema.sql
psql -d sih_procurement -f database/seed.sql
```

#### Step 2: Compile C Module
```bash
make -C c_modules clean
make -C c_modules
# Output: c_modules/libcqueue.dylib (or .so on Linux)
```

#### Step 3: Compile C++ Module
```bash
make -C cpp_modules clean
make -C cpp_modules
# Output: cpp_modules/libcppqueue_opt.dylib (or .so on Linux)
```

#### Step 4: Python Virtual Environment & Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Step 5: Run Automated Test Suite
```bash
PYTHONPATH=. pytest -v tests/
# Runs all 16 unit, integration, and database tests
```

#### Step 6: Start Backend & Frontend Server
```bash
PYTHONPATH=. uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Navigate to **http://localhost:8000** in any browser.

---

## 5. Demo Login Credentials

The application includes one-click demo login buttons directly on the landing page for immediate SIH judge presentation:

| Role | Username | Password | Context & Pre-Populated State |
| :--- | :--- | :--- | :--- |
| **Farmer** | `farmer1` | `farmer123` | **Ramesh Kumar Goud** (Kudakuda, Suryapet). Holds **Token A023** (5 farmers ahead, wait time ~20 min, status `IN QUEUE`). |
| **Official** | `official1` | `official123` | **Venkat Reddy**, Senior Inspector at **Central Procurement Center - Suryapet**. Currently processing Token A018 with 7 waiting farmers. |
| **Admin** | `admin1` | `admin123` | **Dr. K. Srinivas Rao, IAS**, State Directorate. Monitors state-wide KPIs, SVG analytics, and C++ optimization runner. |

---

## 6. Key REST API Endpoints

### Authentication
- `POST /api/auth/register` — Register a new farmer with land & crop details.
- `POST /api/auth/login` — Authenticate and receive JWT access token.
- `POST /api/auth/demo-login/{role}` — One-click demo login (`farmer`, `official`, `admin`).
- `GET /api/auth/me` — Retrieve profile of currently authenticated user.

### Farmer Endpoints
- `GET /api/farmer/profile` — Full agricultural profile (land, crop, bank details).
- `GET /api/farmer/schedules` — Available procurement schedules by center & commodity.
- `POST /api/farmer/book` — Book procurement slot and invoke C engine to generate token.
- `GET /api/farmer/active-token` — Live queue position, current token, and wait time calculation.
- `GET /api/farmer/history` — Procurement transactions, net weights, moisture %, and DBT amounts.
- `GET /api/farmer/notifications` — Farmer alert feed.

### Official Endpoints
- `GET /api/official/dashboard` — Today's center stats, waiting count, active token.
- `GET /api/official/queue` — Full roster of today's queued farmers.
- `POST /api/official/call-next` — Advance queue to next farmer & broadcast real-time WebSocket event.
- `POST /api/official/complete-token` — Record weighbridge gross/tare weights, moisture %, and complete transaction.
- `POST /api/official/skip-token` — Handle absent/no-show farmer.
- `POST /api/official/update-center-status` — Set center status (`OPEN`, `PAUSED`, `DELAYED`, `CLOSED`).
- `POST /api/official/announcements` — Broadcast emergency announcement.

### Admin Endpoints
- `GET /api/admin/dashboard` — State-wide KPIs (farmers, centers, MT procured, DBT disbursed).
- `GET /api/admin/centers` — Manage procurement centers.
- `GET /api/admin/reports` — Commodity-wise and center-wise analytical breakdown.
- `POST /api/admin/run-cpp-optimization` — Execute C++ workload optimization model.
- `POST /api/admin/run-cpp-simulation` — Run C++ discrete-event stochastic day simulation.

### WebSocket Endpoint
- `/ws/live?center_id={id}&user_id={id}` — Bi-directional real-time feed for token advancements, status alerts, and audio cues.

---

## 7. SIH 2026 Presentation & Demonstration Workflow

For an impressive Smart India Hackathon presentation, follow this 4-step live demonstration:

### Step 1: Farmer View (The Problem & The Digital Token)
1. Open `http://localhost:8000` and click **"👨‍🌾 Demo Farmer"** to log in as Ramesh Kumar.
2. Note the prominent **Live Token Card**:
   - **Your Token:** `A023`
   - **Current Serving:** `A018`
   - **Farmers Ahead:** `5`
   - **Estimated Wait:** `20 min` (calculated by the compiled C engine!)
3. Click **"🎫 Digital Pass"** to display the official printable pass with the pure SVG QR code and CRC8 tamper-evident checksum.
4. Click the language switcher (**हिन्दी** or **తెలుగు**) to show instant, seamless localized translation.

### Step 2: Live Real-Time Queue Movement (The Core Innovation)
1. Open a second browser window side-by-side at `http://localhost:8000`.
2. Click **"🏢 Demo Official"** to log in as Inspector Venkat Reddy.
3. On the Official screen, click **"📢 CALL NEXT FARMER"**.
4. **Observe the Farmer window:**
   - **Without refreshing the page**, the Farmer dashboard instantly updates via WebSockets!
   - Current serving advances to `A019`.
   - Farmers ahead drops from `5` to `4`!
   - Estimated wait time decreases immediately!
   - Audio chime rings automatically!

### Step 3: Weighbridge & DBT Transaction Completion
1. On the Official dashboard, click **"⚖️ Complete & Weigh"**.
2. Record Gross Weight (`42.50` Qtl), Tare Weight (`2.50` Qtl), and Moisture (`14.2%`).
3. Click **"Save & Complete Procurement"**.
4. Switch to the Farmer screen and click **"📜 Procurement History"** to view the instant receipt with DBT payout credit.

### Step 4: State Admin & C++ Optimization Showcase
1. Click **"Sign Out"** and log in as **"🏛️ Demo State Administrator"**.
2. View state-wide procurement metrics and pure SVG analytical charts.
3. Scroll to the **C++ Workload & Scheduling Optimizer** section.
4. Click **"⚙️ Run C++ Workload Optimizer"** and **"🎲 Run Stochastic Simulation"** to demonstrate the native C++ algorithm analyzing bottleneck hours and counter utilization in real time.
