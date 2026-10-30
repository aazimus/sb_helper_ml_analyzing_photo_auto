from django.db import models
import os


class ChatGroup(models.Model):
    chat_id = models.CharField(max_length=255, unique=True, verbose_name="ID чата в MAX")
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название чата")
    is_active = models.BooleanField(default=True, verbose_name="Активен (отслеживать)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата первого обращения")

    def __str__(self):
        status = "Активен" if self.is_active else "Заблокирован"
        return f"{self.name or self.chat_id} ({status})"

    class Meta:
        verbose_name = "Группа (Чат)"
        verbose_name_plural = "Группы (Чаты)"


class CarPhotoRecord(models.Model):
    STATUS_CHOICES = [
        ('pending', 'В очереди'),
        ('processing', 'Обрабатывается'),
        ('success', 'Успешно'),
        ('error', 'Ошибка'),
    ]

    group_name = models.CharField(
        max_length=255,
        default="default-group",
        verbose_name='Группа/проект',
    )

    # Исходный путь или URL (откуда пришло фото)
    photo_path = models.CharField(
        max_length=1024,
        verbose_name='Исходный путь / URL',
        null=True,
        blank=True,
    )

    # Сохранённые файлы в media/
    original_image = models.ImageField(
        upload_to='car_photos/originals/',
        verbose_name='Оригинал',
        null=True,
        blank=True,
    )

    crop_image = models.ImageField(
        upload_to='car_photos/crops/',
        verbose_name='Кроп номера',
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус',
    )

    plate_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Распознанный номер',
    )

    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name='Ошибка',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создано',
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Обновлено',
    )

    class Meta:
        verbose_name = 'Фото авто'
        verbose_name_plural = 'Фото авто'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['plate_number']),
            models.Index(fields=['group_name']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        plate = self.plate_number or 'НЕ РАСПОЗНАН'
        return f"[{plate}] Группа: {self.group_name} ({self.get_status_display()})"