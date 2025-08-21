from rest_framework import serializers
from rest_framework.serializers import ListField

from .models import Order, OrderProducts


class OrderProductsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderProducts
        fields = ['product', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    products = ListField(
        child = OrderProductsSerializer(),
        allow_empty=False,
        write_only=True
    )

    class Meta:
        model = Order
        fields = '__all__'
