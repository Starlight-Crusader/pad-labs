#!/bin/bash
set -e

# Check if the environment variable RUN_MIGRATIONS is set to "true"
if [ "$RUN_MIGRATIONS" == "true" ]; then
    echo "Running migrations..."
    python manage.py makemigrations
    python manage.py migrate --noinput
else
    echo "Skipping migrations (RUN_MIGRATIONS is set to false)."
fi

# Register the service with the service discovery component
python grpc_registration/register_service.py

# Start the application
exec gunicorn --bind 0.0.0.0:8000 sA.wsgi:application --reload --access-logfile '-'
