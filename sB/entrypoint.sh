#!/bin/bash
set -e

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Register the service with the service discovery component
python grpc_registration/register_service.py

# Start the application
exec uvicorn sB.asgi:application --host 0.0.0.0 --port 8000 --reload --no-access-log