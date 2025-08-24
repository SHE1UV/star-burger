import requests
import logging

from geopy import distance
from operator import itemgetter

from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.conf import settings

from foodcartapp.models import Product, Restaurant, Order
from geoinfostore.models import Address  


class Login(forms.Form):
    username = forms.CharField(
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={'form': form})

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff: # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(request, "login.html", context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    products_with_restaurant_availability = []
    for product in products:
        availability = {
            item.restaurant_id: item.availability
            for item in product.menu_items.all()
        }
        ordered_availability = [availability.get(restaurant.id, False) for restaurant in restaurants]

        products_with_restaurant_availability.append(
            (product, ordered_availability)
        )

    return render(request, "products_list.html", context={
        'products_with_restaurant_availability': products_with_restaurant_availability,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, "restaurants_list.html", context={
        'restaurants': Restaurant.objects.all(),
    })


def get_geo_objects(apikey, address):
    """Запрашивает геообъекты у Яндекс.Карт"""
    response = requests.get("https://geocode-maps.yandex.ru/1.x", params={
        "geocode": address,
        "apikey": apikey,
        "format": "json",
    })
    response.raise_for_status()
    data = response.json()
    feature_members = data.get('response', {}).get('GeoObjectCollection', {}).get('featureMember', [])
    return feature_members


def get_or_create_address(apikey, address):
    """Возвращает координаты адреса (берёт из БД или запрашивает у API)"""
    obj, created = Address.objects.get_or_create(raw_address=address)

    if not obj.latitude or not obj.longitude:
        geo_objects = get_geo_objects(apikey, address)
        if not geo_objects:
            logging.warning(f'Не удалось найти координаты для адреса: {address}')
            return None

        geo_object = geo_objects[0]['GeoObject']['Point']['pos']
        lon_str, lat_str = geo_object.split()
        obj.latitude, obj.longitude = lat_str, lon_str
        obj.save()

    return (obj.latitude, obj.longitude)


def distance_calculation(apikey, first_address, second_address):
    """Считает расстояние между двумя адресами в км"""
    first_coords = get_or_create_address(apikey, first_address)
    if not first_coords:
        return None

    second_coords = get_or_create_address(apikey, second_address)
    if not second_coords:
        return None

    return distance.distance(
        (float(first_coords[0]), float(first_coords[1])),
        (float(second_coords[0]), float(second_coords[1]))
    ).km


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    yandex_api_key = settings.YANDEX_API_KEY

    orders = (
        Order.objects
        .with_total_price()
        .select_related('restaurant')
        .prefetch_related('orderproducts__product')
    )

    restaurants = list(
        Restaurant.objects.all().prefetch_related('menu_items__product')
    )

    restaurant_products_map = {}
    for restaurant in restaurants:
        available_products = {
            item.product.name
            for item in restaurant.menu_items.all()
            if item.availability
        }
        restaurant_products_map[restaurant.id] = available_products

    order_items = []

    for order in orders:
        order_status = order.get_status_display()
        order_address = order.address

        if order_status == 'В пути':
            order_restaurant_info = 'Заказ уже в пути'

        elif not order.restaurant:
            order_products = order.orderproducts.all()
            product_names = {p.product.name for p in order_products}

            capable_restaurants = []

            for restaurant in restaurants:
                restaurant_products = restaurant_products_map.get(restaurant.id, set())

                distance_from_restaurant = None
                restaurant_address = restaurant.address

                if restaurant_address and order_address:
                    distance_from_restaurant = distance_calculation(
                        yandex_api_key,
                        restaurant_address,
                        order_address
                    )

                if product_names.issubset(restaurant_products):
                    capable_restaurants.append(
                        (restaurant.name, distance_from_restaurant)
                    )

            sorted_capable_restaurants = sorted(
                capable_restaurants,
                key=itemgetter(1, 0)
            )

            formatted_capable_restaurants = []
            for name, dist in sorted_capable_restaurants:
                if dist is not None:
                    formatted_capable_restaurants.append(f"{name} - {dist:.2f} км")
                else:
                    formatted_capable_restaurants.append(name)

            formatted_capable_restaurants = ', '.join(formatted_capable_restaurants)

            order_restaurant_info = (
                f'Рестораны которые могут приготовить заказ: '
                f'<li class="restaurants-marker">{formatted_capable_restaurants}</li>'
            )

        else:
            order_restaurant_info = f"Готовится в: {order.restaurant}"

        order_item = {
            'id': order.id,
            'status': order_status,
            'payment_method': order.get_payment_method_display(),
            'client': f"{order.firstname} {order.lastname}",
            'phonenumber': order.phonenumber,
            'address': order_address,
            'order_cost': order.total_price,
            'comment': order.comment_from_manager,
            'restaurant': order_restaurant_info,
        }

        order_items.append(order_item)

    status_priority = {
        'Выполнен': 1,
        'Необработанный': 2,
        'Готовится': 3,
        'В пути': 4
    }

    filtered_order_items = [
        item for item in order_items if item['status'] != 'Выполнен'
    ]

    sorted_order_items = sorted(
        filtered_order_items,
        key=lambda x: status_priority.get(x['status'], 999)
    )

    return render(request, 'order_items.html', {
        'order_items': sorted_order_items,
    })
