#!/bin/bash
set -e

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Start the application
exec uvicorn sB.asgi:application --host 0.0.0.0 --port 8000 --reload