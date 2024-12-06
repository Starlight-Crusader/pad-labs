#!/bin/bash

# Run migrations on all databases
python manage.py makemigrations
sleep 10
python manage.py migrate --database=default

# Stop the container by exiting the script
echo "Migrations completed. Stopping container."
exit 0
