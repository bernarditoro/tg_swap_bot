from django.core.management.base import BaseCommand

from ads.models import Ad


class Command(BaseCommand):
    help = 'Resets the daily showtime counter of all ads'

    def handle(self, *args, **options):
        ads = Ad.objects.filter(is_running=True)

        for ad in ads:
            ad.daily_showtime_counter = 0
            ad.save()

        self.stdout.write(
            self.style.SUCCESS('Successfully reset all daily showtime counter')
        )

