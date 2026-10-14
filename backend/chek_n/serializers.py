# chek_n/serializers.py
from rest_framework import serializers
from .models import CarPhotoRecord


class CarPhotoRecordSerializer(serializers.ModelSerializer):
    crop_url = serializers.SerializerMethodField()
    original_url = serializers.SerializerMethodField()

    class Meta:
        model = CarPhotoRecord
        fields = [
            'id',
            'plate_number',
            'group_name',
            'status',
            'created_at',
            'crop_url',
            'original_url',
            'photo_path',
        ]

    def get_crop_url(self, obj):
        request = self.context.get('request')
        if obj.crop_image:
            url = obj.crop_image.url
            return request.build_absolute_uri(url) if request else url
        return None

    def get_original_url(self, obj):
        request = self.context.get('request')
        if obj.original_image:
            url = obj.original_image.url
            return request.build_absolute_uri(url) if request else url
        return None