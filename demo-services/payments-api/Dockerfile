FROM python:3.13-slim
WORKDIR /app
COPY common /app/common
COPY payments-api /app/payments-api
RUN pip install --no-cache-dir Django==5.2.8 djangorestframework==3.16.1 psycopg[binary]==3.2.10 celery==5.5.3 redis==6.4.0
ENV PYTHONPATH=/app
WORKDIR /app/payments-api
CMD ["sh", "-c", "python manage.py makemigrations payments --noinput && python manage.py migrate --run-syncdb --noinput --fake-initial && python manage.py runserver 0.0.0.0:8080"]
