# chek_n/api_views.py
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters import rest_framework as filters
from django.db.models import Q

from .models import CarPhotoRecord
from .serializers import CarPhotoRecordSerializer


class CarPhotoRecordFilter(filters.FilterSet):
    group = filters.CharFilter(field_name='group_name', lookup_expr='iexact')
    date_from = filters.DateFilter(field_name='created_at', lookup_expr='date__gte')
    date_to = filters.DateFilter(field_name='created_at', lookup_expr='date__lte')
    search = filters.CharFilter(method='filter_search')

    class Meta:
        model = CarPhotoRecord
        fields = ['group', 'date_from', 'date_to', 'search']

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(plate_number__icontains=value)


class RecordListAPIView(generics.ListAPIView):
    """
    GET /api/records/
    ?group=test-group
    &search=Т777
    &date_from=2026-07-01
    &date_to=2026-07-30
    &page=1
    """
    serializer_class = CarPhotoRecordSerializer
    filterset_class = CarPhotoRecordFilter
    ordering_fields = ['created_at', 'plate_number', 'group_name']
    ordering = ['-created_at']

    def get_queryset(self):
        return CarPhotoRecord.objects.filter(status='success')


class RecordDetailAPIView(generics.RetrieveAPIView):
    """GET /api/records/{id}/"""
    serializer_class = CarPhotoRecordSerializer
    queryset = CarPhotoRecord.objects.filter(status='success')


class GroupListAPIView(APIView):
    """GET /api/groups/ — список уникальных групп"""

    def get(self, request):
        groups = (
            CarPhotoRecord.objects
            .filter(status='success')
            .values_list('group_name', flat=True)
            .distinct()
            .order_by('group_name')
        )
        return Response(list(groups))