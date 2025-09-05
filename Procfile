release: python manage.py migrate && python manage.py setup_production
web: gunicorn claims_system.wsgi:application
