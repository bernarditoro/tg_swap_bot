from django.db import models

from decimal import Decimal

# Create your models here.
class Swap(models.Model):
    NETWORK_CHOICES = (
        ('Ethereum', 'eth'),
        ('Base', 'base')
    )

    destination_address = models.CharField(max_length=70, help_text='Wallet address of the dev initiating the swap')
    token_address = models.CharField(max_length=70)
    blockchain_network = models.CharField(choices=NETWORK_CHOICES, max_length=20, default='eth')
    origin_hash = models.CharField(max_length=70, unique=True, help_text='The hash of the transaction from the dev to the swap account')
    amount_received = models.DecimalField(max_digits=20, decimal_places=18, null=True, blank=True, help_text="The amount (in ethers) that was received from the initiator")
    amount_swapped = models.DecimalField(max_digits=20, decimal_places=18, null=True, blank=True, help_text="The amount (in ethers) that was swapped")
    swap_hash = models.CharField(max_length=70, unique=True, null=True, blank=True)
    wallet_balance_before = models.DecimalField(max_digits=20, decimal_places=18, blank=True, null=True, help_text='The wallet balance of the wallet from where the swap is initiated right before the swap')
    wallet_balance_after = models.DecimalField(max_digits=20, decimal_places=18, blank=True, null=True, help_text='The wallet balance of the wallet from where the swap is initiated after the swap')
    is_successful = models.BooleanField(default=False)
    date_initiated = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.origin_hash
    
    def get_total_spent(self):
        """Get the total amount used"""
        return self.wallet_balance_before - self.wallet_balance_after if self.wallet_balance_before and self.wallet_balance_after else 0
    
    def get_gas_fees(self):
        return self.get_total_spent() - self.swap_amount if self.swap_amount else 0
    
    def get_swap_amount(self):
        """Deduct 20% for gas and misc"""

        return self.amount_swapped if self.amount_swapped else (Decimal(0.8) * self.amount_received)
