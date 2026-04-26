#!/bin/bash
echo "Starting backend..."
cd backend
python -m uvicorn main:app --port 8000 &
BACKEND_PID=$!

echo "Backend started on port 8000."
echo "Starting frontend server..."

cd ../frontend
python -m http.server 3000 &
FRONTEND_PID=$!

echo "Frontend started on http://localhost:3000/"
echo "Press Ctrl+C to stop both."

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
