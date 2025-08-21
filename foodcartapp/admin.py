from django.contrib import admin
from django.shortcuts import reverse
from django.templatetags.static import static
from django.utils.html import format_html

from .models import Product
from .models import ProductCategory
from .models import Restaurant
from .models import RestaurantMenuItem
from .models import Order, OrderProducts

from django import forms
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect


class RestaurantMenuItemInline(admin.TabularInline):
    model = RestaurantMenuItem
    extra = 0


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    search_fields = [
        'name',
        'address',
        'contact_phone',
    ]
    list_display = [
        'name',
        'address',
        'contact_phone',
    ]
    inlines = [
        RestaurantMenuItemInline
    ]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'get_image_list_preview',
        'name',
        'category',
        'price',
    ]
    list_display_links = [
        'name',
    ]
    list_filter = [
        'category',
    ]
    search_fields = [
        # FIXME SQLite can not convert letter case for cyrillic words properly, so search will be buggy.
        # Migration to PostgreSQL is necessary
        'name',
        'category__name',
    ]

    inlines = [
        RestaurantMenuItemInline
    ]
    fieldsets = (
        ('Общее', {
            'fields': [
                'name',
                'category',
                'image',
                'get_image_preview',
                'price',
            ]
        }),
        ('Подробно', {
            'fields': [
                'special_status',
                'description',
            ],
            'classes': [
                'wide'
            ],
        }),
    )

    readonly_fields = [
        'get_image_preview',
    ]

    class Media:
        css = {
            "all": (
                static("admin/foodcartapp.css")
            )
        }

    def get_image_preview(self, obj):
        if not obj.image:
            return 'выберите картинку'
        return format_html('<img src="{url}" style="max-height: 200px;"/>', url=obj.image.url)
    get_image_preview.short_description = 'превью'

    def get_image_list_preview(self, obj):
        if not obj.image or not obj.id:
            return 'нет картинки'
        edit_url = reverse('admin:foodcartapp_product_change', args=(obj.id,))
        return format_html('<a href="{edit_url}"><img src="{src}" style="max-height: 50px;"/></a>', edit_url=edit_url, src=obj.image.url)
    get_image_list_preview.short_description = 'превью'


@admin.register(ProductCategory)
class ProductAdmin(admin.ModelAdmin):
    pass


class OrderProductsForm(forms.ModelForm):
    class Meta:
        model = OrderProducts
        fields = '__all__'

    def clean(self):
        cleaned_info = super().clean()
        product = cleaned_info.get('product')
        order = cleaned_info.get('order')

        if product and order:
            try:
                cleaned_info['price'] = product.price
            except RestaurantMenuItem.DoesNotExist:
                raise ValidationError(f"Нет товара {product.name}")
        return cleaned_info

class OrderProductsInline(admin.TabularInline):
    model = OrderProducts
    extra = 1
    form = OrderProductsForm

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderProductsInline]

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            obj.save()
        formset.save_m2m()

    def change_view(self, request, object_id, form_url='', extra_context=None):
        next_url = request.GET.get('next', '')
        if next_url:
            request.session['order_next_url'] = next_url
        return super().change_view(request, object_id, form_url, extra_context)

    def response_change(self, request, obj):
        previous_path = request.META.get('HTTP_REFERER', '')

        if '_save' in request.POST:
            redirect_url = request.session.pop('order_next_url', None)
            if redirect_url:
                return HttpResponseRedirect(redirect_url)

            else:
                if 'order_items.html' in previous_path:
                    redirect_url = '/manager/orders'

                elif 'admin/' in previous_path:
                    redirect_url = '/admin/foodcartapp/order/'

                elif url_has_allowed_host_and_scheme(
                    previous_path, allowed_hosts={request.get_host()}
                ):
                    redirect_url = previous_path

                else:
                    redirect_url = '/admin/foodcartapp/order/'

                return HttpResponseRedirect(redirect_url)

        return super().response_change(request, obj)
