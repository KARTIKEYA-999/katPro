#!/usr/bin/env bash
set -e

echo "================================================================================"
echo "SMART INDIA HACKATHON 2026 - PS ID: 26032"
echo "Digital System for Procurement Schedules, Farmer Queues & Real-Time Status"
echo "================================================================================"

# 1. Ensure PostgreSQL binary path is present
export PATH="/opt/homebrew/opt/postgresql@16/bin:/opt/homebrew/bin:$PATH"

# 2. Start PostgreSQL 16 server if not running
if ! pg_isready -q 2>/dev/null; then
    echo "[1/5] Starting PostgreSQL 16 background server..."
    pg_ctl -D /opt/homebrew/var/postgresql@16 -l /opt/homebrew/var/postgresql@16/server.log start || true
    sleep 2
else
    echo "[1/5] PostgreSQL 16 server is active."
fi

# 3. Create database if it does not exist
createdb sih_procurement 2>/dev/null || true

# 4. Compile C Performance Acceleration Library
echo "[2/5] Compiling C Module (libcqueue)..."
make -C c_modules clean
make -C c_modules

# 5. Compile C++ Advanced Workload Optimization Library
echo "[3/5] Compiling C++ Module (libcppqueue_opt)..."
make -C cpp_modules clean
make -C cpp_modules

# 6. Initialize Virtual Environment & Apply Database Schema/Seed
echo "[4/5] Checking Python Virtual Environment & Database Seed..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

# Execute PostgreSQL schema & seed
psql -d sih_procurement -f database/schema.sql > /dev/null 2>&1
psql -d sih_procurement -f database/seed.sql > /dev/null 2>&1
echo "      PostgreSQL tables, indexes, views, and 22 seed farmers loaded."

# 7. Start Uvicorn Full-Stack Server
echo "[5/5] Launching SIH 2026 Full-Stack Application on http://localhost:8000..."
echo "--------------------------------------------------------------------------------"
echo "  🌾 Portal URL:     http://localhost:8000"
echo "  👨‍🌾 Farmer Demo:    farmer1   / farmer123  (Token A023)"
echo "  🏢 Official Demo:  official1 / official123 (Suryapet CPC)"
echo "  🏛️ Admin Demo:     admin1    / admin123"
echo "--------------------------------------------------------------------------------"

PYTHONPATH=. uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
