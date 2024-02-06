from django.contrib import admin

from .models import Swap


# Register your models here.
@admin.register(Swap)
class SwapAdmin(admin.ModelAdmin):
    list_display = ['origin_hash', 'token_address', 'swap_hash', 'destination_address', 'get_transaction_fees', 'date_initiated']