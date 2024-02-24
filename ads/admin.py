from django.contrib import admin

from .models import Ad


# Register your models here.
@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = ['ad_text', 'amount_paid', 'daily_showtime_counter']
