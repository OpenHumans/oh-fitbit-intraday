release: python manage.py migrate
web: gunicorn fitbit_app.wsgi:application --log-file -
worker: celery worker -A main --concurrency 1
