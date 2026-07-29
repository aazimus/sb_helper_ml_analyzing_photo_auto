from django.db import models
from django.conf import settings
import os

class CarPhotoRecord(models.Model):
    STATUS_CHOICES = [
        ('pending', 'В очереди'),
        ('processing', 'Обрабатывается'),
        ('success', 'Успешно'),
        ('error', 'Ошибка'),
    ]

    group_name = models.CharField(
        max_length=255,
        verbose_name='Группа/проект',
    )

    # Разрешаем null/blank, чтобы миграции прошли без вопросов про старые строки
    photo_path = models.FilePathField(
        path=settings.TEST_PHOTOS_DIR,
        match=r'.*\.(jpg|jpeg|png|webp)$',
        allow_files=True,
        allow_folders=False,
        verbose_name='Путь к файлу',
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

    # Тоже делаем nullable на время, чтобы не было диалогов про default
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

    def __str__(self):
        filename = os.path.basename(self.photo_path) if self.photo_path else 'без файла'
        return f"{self.group_name} | {filename} | {self.get_status_display()}"