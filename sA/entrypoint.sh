#!/bin/bash
set -e

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Start the application
exec gunicorn --bind 0.0.0.0:8000 sA.wsgi:application