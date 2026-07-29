from rest_framework import serializers
from .models import CarPhotoRecord

class CarPhotoRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarPhotoRecord
        fields = ['group_name', 'photo_url', 'detected_plate', 'status']
        # detected_plate и status мы пока не даём менять снаружи, но для простоты оставим в полях.
        # Позже можно будет сделать их read_only.