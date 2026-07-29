
from django.urls import path
from .views import webhook_simple, finish_processing  # <-- важно: обе функции через запятую

urlpatterns = [
    path('webhook/', webhook_simple, name='webhook_simple'),
    path('finish/<int:record_id>/', finish_processing, name='finish_processing'),  # <-- этот путь теперь будет работать
]