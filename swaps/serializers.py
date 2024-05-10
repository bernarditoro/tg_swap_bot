from rest_framework import serializers

from .models import Swap


class SwapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Swap
        fields = ['destination_address', 'token_address', 'origin_hash', 'amount_received', 'blockchain_network', 'is_successful']
