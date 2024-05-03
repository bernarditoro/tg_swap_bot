from rest_framework.generics import RetrieveAPIView, CreateAPIView

from .serializers import AdSerializer
from .models import Ad

from django.db.models import ExpressionWrapper, F, FloatField

import random


# Create your views here.

class AdPreviewView(RetrieveAPIView):
    serializer_class = AdSerializer
    queryset = Ad.objects.all()

    def get_object(self):
        running_ads = Ad.objects.filter(is_running=True).annotate(
            ad_weight=ExpressionWrapper(
                F('amount_paid') / F('showtime_duration'),
                output_field=FloatField()
            )
        ).order_by('ad_weight')

        ads_count = running_ads.count()

        while ads_count > 0:
            ad = running_ads[random.randint(0, ads_count - 1)]

            if ad.daily_showtime_counter <= round(ad.max_daily_showtime):
                ad.daily_showtime_counter += 1
                ad.save()

                return ad
            
            ads_count -= 1


class AdCreateView(CreateAPIView):
    serializer_class = AdSerializer
    queryset = Ad.objects.all()
