from django.urls import path

from . import views


app_name = 'swaps'

urlpatterns = [
    path('', views.SwapListView.as_view(), name='swaps_list'),
    path('create/', views.SwapCreateView.as_view(), name='create_swap'),
    path('swap/', views.SwapAPIView.as_view(), name='execute_swap'),
]
