from .serializers import SwapSerializer

from rest_framework.generics import CreateAPIView, GenericAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework import status

from .models import Swap
from .swap import swap_eth_for_tokens

import logging


# Configuration for the root logger with a file handler
logging.basicConfig(
    level=logging.INFO,
    filename='logs/logs.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


# Create your views here.
class SwapCreateView(CreateAPIView):
    serializer_class = SwapSerializer
    queryset = Swap.objects.all()

    def create(self, request, *args, **kwargs):
        print (request.data)

        return super().create(request, *args, **kwargs)


class SwapAPIView(GenericAPIView):
    def get(self, request, *args, **kwargs):
        params = request.GET

        network = params.get('network', None)
        origin_hash = params.get('origin_hash', None)
        recipient_address = params.get('recipient_address', None)
        token_address = params.get('token_address', None)

        if (network and origin_hash and recipient_address and token_address):
            try:
                tx_hash, receipt = swap_eth_for_tokens(network, origin_hash, recipient_address, token_address)

                return Response({'tx_hash': tx_hash, 'receipt': receipt})
            
            except Exception as e:
                logger.info(f'Exception occurred while executing swap ({request.GET}): {e}')

                return Response({'error': 'Could not execute swap'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        else:
            return Response({'error': 'Swap parameters missing'}, status=status.HTTP_400_BAD_REQUEST)
        

class SwapListView(ListAPIView):
    serializer_class = SwapSerializer

    def get_queryset(self):
        queryset = Swap.objects.all()

        if params:=self.request.GET:
            filters = {}
                
            for key, value in params.items():
                filters[key] = value

            queryset = queryset.filter(**filters)
            
        return queryset
