from django.contrib import admin

from .models import Swap


# Register your models here.
@admin.register(Swap)
class SwapAdmin(admin.ModelAdmin):
    list_display = ['origin_hash', 'token_address', 'get_transaction_fees', 'swap_hash', 'destination_address', 'date_initiated']