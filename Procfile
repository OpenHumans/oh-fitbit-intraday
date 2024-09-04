release: python manage.py migrate
web: gunicorn fitbit_app.wsgi:application --log-file -
worker: celery -A main worker --concurrency 1
