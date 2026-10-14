FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1
ENV REDIS_URL=redis://redis:6379/0

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "cheking_number_car.wsgi:application"]