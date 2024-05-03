from rest_framework import serializers

from .models import Ad


class AdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ad
        exclude = ['date_created', 'total_times_shown', 'daily_showtime_counter']
