# chek_n/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import CarPhotoRecord
import os


@admin.register(CarPhotoRecord)
class CarPhotoRecordAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'group_name',          # группа на первом месте после id
        'plate_number',
        'crop_preview',
        'created_at_display',
        'status_display',
    )
    list_filter = ('group_name', 'status', 'created_at')
    search_fields = ('plate_number', 'group_name', 'photo_path')
    readonly_fields = (
        'created_at', 'updated_at',
        'original_preview', 'crop_preview_large',
    )
    ordering = ['-created_at']
    list_per_page = 50
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Основное', {
            'fields': ('group_name', 'plate_number', 'status', 'photo_path')
        }),
        ('Изображения', {
            'fields': (
                'original_image', 'original_preview',
                'crop_image', 'crop_preview_large',
            )
        }),
        ('Служебное', {
            'fields': ('error_message', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def crop_preview(self, obj):
        if obj.crop_image:
            return format_html(
                '<img src="{}" style="height:36px;border-radius:3px;" />',
                obj.crop_image.url
            )
        return '—'
    crop_preview.short_description = 'Кроп'

    def original_preview(self, obj):
        if obj.original_image:
            return format_html(
                '<img src="{}" style="max-height:280px;border-radius:6px;" />',
                obj.original_image.url
            )
        return '—'
    original_preview.short_description = 'Оригинал'

    def crop_preview_large(self, obj):
        if obj.crop_image:
            return format_html(
                '<img src="{}" style="max-height:110px;border-radius:4px;" />',
                obj.crop_image.url
            )
        return '—'
    crop_preview_large.short_description = 'Кроп (крупно)'

    def status_display(self, obj):
        return obj.get_status_display()
    status_display.short_description = 'Статус'
    status_display.admin_order_field = 'status'

    def created_at_display(self, obj):
        if not obj.created_at:
            return '—'
        return obj.created_at.strftime('%d.%m.%Y %H:%M')
    created_at_display.short_description = 'Дата'
    created_at_display.admin_order_field = 'created_at'