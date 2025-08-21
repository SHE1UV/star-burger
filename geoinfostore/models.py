from django.db import models

class GeocodingAddresses(models.Model):
    first_address = models.CharField(
        'Первый адрес', 
        max_length=255, 
        null=True
    )
    first_address_latitude = models.DecimalField(
        'Широта первого адреса', 
        max_digits=9, 
        decimal_places=6, 
        null=True
    )
    first_address_longitude = models.DecimalField(
        'Долгота первого адреса', 
        max_digits=9, 
        decimal_places=6, 
        null=True
    )

    second_address = models.CharField(
        'Второй адрес', 
        max_length=255, 
        null=True
    )
    second_address_latitude = models.DecimalField(
        'Широта второго адреса', 
        max_digits=9, 
        decimal_places=6, 
        null=True
    )
    second_address_longitude = models.DecimalField(
        'Долгота второго адреса', 
        max_digits=9, 
        decimal_places=6, 
        null=True
    )

    distance = models.FloatField('Расстояние между адресами (км)', null=True, blank=True)

    last_updated = models.DateTimeField('Последнее обновление', auto_now=True)

    class Meta:
        unique_together = ('first_address', 'second_address')

    def __str__(self):
        return (f"""{self.first_address} - ({self.first_address_latitude}, {self.first_address_longitude})
                    {self.second_address} - ({self.second_address_latitude}, {self.second_address_longitude})""")
