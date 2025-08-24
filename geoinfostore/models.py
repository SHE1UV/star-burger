from django.db import models

class Address(models.Model):
    raw_address = models.CharField('Адрес', max_length=255, unique=True)
    latitude = models.DecimalField(
        'Широта',
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        'Долгота',
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    last_updated = models.DateTimeField('Последнее обновление', auto_now=True)

    def __str__(self):
        return f"{self.raw_address} ({self.latitude}, {self.longitude})"
