# chek_n/urls.py
from django.urls import path
from .views import webhook_simple, finish_processing
from .api_views import RecordListAPIView, RecordDetailAPIView, GroupListAPIView

urlpatterns = [
    # webhook (эмулятор / Max)
    path('webhook/', webhook_simple, name='webhook_simple'),
    path('finish/<int:record_id>/', finish_processing, name='finish_processing'),

    # API для фронта
    path('records/', RecordListAPIView.as_view(), name='record-list'),
    path('records/<int:pk>/', RecordDetailAPIView.as_view(), name='record-detail'),
    path('groups/', GroupListAPIView.as_view(), name='group-list'),
]