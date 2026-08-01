from django.db import models
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

    # Исходный путь (откуда пришло фото)
    photo_path = models.CharField(
        max_length=500,
        verbose_name='Исходный путь',
        null=True,
        blank=True,
    )

    # Сохранённые файлы в media/
    original_image = models.ImageField(
        upload_to='originals/',
        verbose_name='Оригинал',
        null=True,
        blank=True,
    )

    crop_image = models.ImageField(
        upload_to='crops/',
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

    def __str__(self):
        filename = os.path.basename(self.photo_path) if self.photo_path else 'без файла'
        return f"{self.group_name} | {filename} | {self.get_status_display()}"