#!/bin/bash

# Restart the queue worker in the orangescrum-v4 container

CONTAINER_NAME="orangescrum-v4"
QUEUE_PROCESS="queue worker"

echo "Finding queue worker process in container: $CONTAINER_NAME"

# Get the process ID
PID=$(docker compose exec $CONTAINER_NAME ps aux | grep "$QUEUE_PROCESS" | grep -v grep | awk '{print $2}')

if [ -z "$PID" ]; then
    echo "Queue worker process not found. Starting new one..."
else
    echo "Found queue worker process with PID: $PID"
    echo "Killing process..."
    docker compose exec $CONTAINER_NAME kill $PID
    
    # Wait for process to terminate
    sleep 2
    echo "Process killed."
fi

echo "Starting new queue worker..."
docker compose exec -d -u appuser $CONTAINER_NAME php bin/cake.php queue worker --verbose

echo "Queue worker restarted successfully!"
echo ""

# Verify it's running
echo "Verifying queue worker is running..."
docker compose exec $CONTAINER_NAME ps aux | grep "$QUEUE_PROCESS" | grep -v grep
