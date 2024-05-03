from django.urls import path

from . import views


app_name = 'ads'

urlpatterns = [
    path('get-random/', views.AdPreviewView.as_view(), name='get_random_ad'),
    path('create/', views.AdCreateView.as_view(), name='create_ad'),
]
