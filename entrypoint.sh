#!/bin/sh
set -e

echo "Waiting for database..."
until python -c "
import os, sys, time
import psycopg2
try:
    conn = psycopg2.connect(
        dbname=os.environ.get('DB_NAME', 'car_db'),
        user=os.environ.get('DB_USER', 'car_user'),
        password=os.environ.get('DB_PASSWORD', 'car_password_123'),
        host=os.environ.get('DB_HOST', 'db'),
        port=os.environ.get('DB_PORT', '5432'),
        connect_timeout=3,
    )
    conn.close()
    print('Database is ready!')
except Exception as e:
    print(f'Database not ready: {e}')
    sys.exit(1)
"; do
    echo "Database not ready, retrying in 2s..."
    sleep 2
done

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear 2>/dev/null || true

echo "Starting server..."
exec "$@"
