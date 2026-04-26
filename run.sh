#!/bin/bash
echo "Starting Schafkopf Tracker (Backend + Frontend)..."
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Server started successfully!"
echo "➡️ Access from PC: http://localhost:8000"
echo "➡️ Access from Phone: http://<deine-IP-Adresse>:8000 (im gleichen WLAN)"
echo "Press Ctrl+C to stop."

trap "kill $BACKEND_PID" EXIT
wait
