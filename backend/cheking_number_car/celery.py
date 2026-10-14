import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cheking_number_car.settings')

app = Celery('cheking_number_car')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()