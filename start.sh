#!/bin/bash

# Railway startup script for Django Claims Management System
# This script ensures proper initialization before starting the web server

set -e  # Exit on any error

echo "🚀 Starting Django Claims Management System deployment (v2)..."
echo "📍 Current directory: $(pwd)"
echo "📁 Files in directory: $(ls -la)"

# Run database migrations
echo "📊 Running database migrations..."
python manage.py migrate --noinput

# Set up production data and users
echo "👥 Setting up production users and sample data..."
python manage.py setup_production

# Collect static files (important for production)
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput --clear

# Start the web server
echo "🌐 Starting Gunicorn web server..."
exec gunicorn claims_system.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
