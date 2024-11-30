from django.urls import path, include
from webpage import views

urlpatterns = [
    path('', views.detail, name='webpage'),
]
