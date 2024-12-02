from django.urls import path, include
from search import views

urlpatterns = [
    path('', views.search, name='search'),
    path('episodes/', views.episodes, name='episodes'),
]
