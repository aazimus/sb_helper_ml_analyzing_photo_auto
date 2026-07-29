# chek_n/admin.py
from django.contrib import admin
from .models import CarPhotoRecord
import os

@admin.register(CarPhotoRecord)
class CarPhotoRecordAdmin(admin.ModelAdmin):
    # Колонки в списке записей
    list_display = ('group_name', 'filename', 'status_display', 'plate_number', 'created_at_display')
    
    # Фильтры справа
    list_filter = ('status', 'group_name')
    
    # Поиск по этим полям
    search_fields = ('group_name', 'plate_number', 'photo_path')

    # Показываем только имя файла вместо полного пути
    def filename(self, obj):
        if not obj.photo_path:
            return '—'
        return os.path.basename(obj.photo_path)
    filename.short_description = 'Файл'

    # Красивый вывод статуса (чтобы не видеть pending/success, а видеть понятные названия)
    def status_display(self, obj):
        return obj.get_status_display()
    status_display.short_description = 'Статус'

    # Красивая дата (без секунд, чтобы было аккуратнее)
    def created_at_display(self, obj):
        if not obj.created_at:
            return '—'
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_display.short_description = 'Создано'

    # Порядок сортировки по умолчанию (уже есть в модели, но можно продублировать тут)
    ordering = ['-created_at']