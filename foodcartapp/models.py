from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from phonenumber_field.modelfields import PhoneNumberField
from django.db.models import F, Sum
from django.utils import timezone


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=200,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name='ресторан',
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class OrderQuerySet(models.QuerySet):
    def with_total_price(self):
        return self.annotate(
            total_price=Sum(F('orderproducts__quantity') * F('orderproducts__price'))
        )

class Order(models.Model):
    firstname = models.CharField(
        'Имя',
        max_length=50,
        null=False,
        blank=False
    ) 
    lastname = models.CharField(
        'Фамилия',
        max_length=50,
        null=False,
        blank=False
    )
    phonenumber = PhoneNumberField('Номер телефона', region='RU')
    address = models.CharField(
        'Адрес доставки',
        max_length=100,
        blank=False,
    )

    ORDER_STATUS = [
        ('U', "Необработанный"),
        ('S', "Готовится"),
        ('D', "В пути"),
        ('V', 'Выполнен')
    ]

    status = models.CharField(
        'Статус заказа',
        max_length=1,
        choices=ORDER_STATUS,
        default='U',
        db_index=True
    )

    comment_from_manager = models.TextField(
        'Комментарий менеджера',
        max_length=200,
        blank=True
    )

    created_at = models.DateTimeField(
        'Дата и время создания',
        default=timezone.now,
        db_index=True
    )
    called_at = models.DateTimeField(
        'Дата и время звонка',
        null=True,
        blank=True,
        db_index=True
    )
    delivered_at = models.DateTimeField(
        'Дата и время доставки',
        null=True,
        blank=True,
        db_index=True
    )

    PAYMENT_METHODS = [
        ('C', 'Наличными'),
        ('E', 'Электронный'),
        ('K', 'Картой'),
    ]

    payment_method = models.CharField(
        'Способ оплаты',
        max_length=1,
        choices=PAYMENT_METHODS,
        default='C',
        db_index=True
    )

    restaurant = models.ForeignKey(
        Restaurant,
        verbose_name='Ресторан для заказа',
        related_name='orders',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    def get_status_display(self):
        return dict(self.ORDER_STATUS).get(self.status)

    def get_payment_method_display(self):
        return dict(self.PAYMENT_METHODS).get(self.payment_method)

    objects = OrderQuerySet.as_manager()
    
    class Meta:
        verbose_name = "Заказ"

    def __str__(self):
        return f"{self.firstname} {self.lastname} - {self.address}"


class OrderProducts(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='orderproducts'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    quantity = models.IntegerField(
        validators=[
            MinValueValidator(0), 
            MaxValueValidator(10000)
        ]
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    def __str__(self):
        return f"{self.order} - {self.product} {self.quantity}"
