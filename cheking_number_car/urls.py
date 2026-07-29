from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('chek_n.urls')),  # <-- вот эта строчка решает всё
]