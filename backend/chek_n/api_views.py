from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters import rest_framework as filters
from django.db.models import Q

from .models import CarPhotoRecord, ChatGroup
from .serializers import CarPhotoRecordSerializer


class CarPhotoRecordFilter(filters.FilterSet):
    group = filters.CharFilter(field_name='group_name', lookup_expr='iexact')
    date_from = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
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
    """GET /api/groups/ — список активных групп из админки"""

    def get(self, request):
        groups = (
            ChatGroup.objects
            .filter(is_active=True)
            .values_list('name', flat=True)
            .order_by('name')
        )
        return Response(list(groups))