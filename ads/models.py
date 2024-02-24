from django.db import models


# Create your models here
class Ad(models.Model):
    telegram_username = models.CharField(max_length=100)

    ad_text = models.TextField()
    external_link = models.URLField()

    amount_paid = models.DecimalField(decimal_places=18, max_digits=20, blank=True, null=True)
    transaction_hash = models.CharField(max_length=70, blank=True, null=True, unique=True)

    showtime_duration = models.SmallIntegerField(help_text='Number of days to show ads')

    is_paid = models.BooleanField(default=False)
    is_running = models.BooleanField(default=False)

    date_created = models.DateTimeField(auto_now_add=True)
    date_ending = models.DateTimeField(blank=True, null=True, help_text='Date ad is due to stop running')

    total_times_shown = models.IntegerField(default=0)
    daily_showtime_counter = models.IntegerField(default=0) # TODO: Create management command to reset showtime_counter daily

    def __str__(self) -> str:
        return self.ad_text

    @property
    def weight(self):
        return float(self.amount_paid/self.showtime_duration)

    @property
    def max_daily_showtime(self):
        return self.weight * 50
