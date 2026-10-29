# chek_n/urls.py

from django.urls import path
from .views import webhook_max, webhook_test  # <-- поменяли импорты
from .api_views import RecordListAPIView, RecordDetailAPIView, GroupListAPIView

urlpatterns = [
  
    path('webhook/max/', webhook_max, name='webhook_max'),

    path('webhook/test/', webhook_test, name='webhook_test'),

    # API 
    path('records/', RecordListAPIView.as_view(), name='record-list'),
    path('records/<int:pk>/', RecordDetailAPIView.as_view(), name='record-detail'),
    path('groups/', GroupListAPIView.as_view(), name='group-list'),
]