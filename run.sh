python manage.py collectstatic --noinput &&
gunicorn gpa.wsgi -c gunicorn.conf.py