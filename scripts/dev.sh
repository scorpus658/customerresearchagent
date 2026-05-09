#!/bin/bash
set -e

echo "Starting development environment..."

# Start Postgres and Redis
docker compose up -d db redis

echo "Waiting for services..."
sleep 3

# Run migrations
cd backend
python -m app.models.database

# Start backend
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start worker
python -m app.workers.pipeline &
WORKER_PID=$!

# Start frontend
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Services running:"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo ""

trap "kill $BACKEND_PID $WORKER_PID $FRONTEND_PID 2>/dev/null; docker compose stop db redis" EXIT
wait
