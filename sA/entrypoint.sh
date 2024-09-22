#!/bin/bash
set -e

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Wait for the API Gateway to be available
# until curl --output /dev/null --silent --fail "$API_GATEWAY_BASE_URL"/; do
#   echo "Waiting for API Gateway..."
#   sleep 2
# done

# # Notify the API Gateway about this service instance
# curl -X POST "$API_GATEWAY_BASE_URL"/register \
#      -H "Content-Type: application/json" \
#      -d '{"service": "A", "ip": "'$(hostname -i)'", "port": 8000}'

# Start the application
exec gunicorn --bind 0.0.0.0:8000 sA.wsgi:application