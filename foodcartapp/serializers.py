from rest_framework import serializers
from .models import Order, OrderProducts


class OrderProductsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderProducts
        fields = ['product', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    products = OrderProductsSerializer(many=True, write_only=True)  # вложенный сериализатор

    class Meta:
        model = Order
        fields = ['id', 'firstname', 'lastname', 'phonenumber', 'address', 'products']

    def create(self, validated_data):
        products = validated_data.pop('products')   # достаём продукты
        order = Order.objects.create(**validated_data)

        order_products = [
            OrderProducts(order=order, **product) for product in products
        ]
        OrderProducts.objects.bulk_create(order_products)

        return order
