from django.urls import path, include
from search import views

urlpatterns = [
    path('', views.home, name='search'),
    path('episodes/', views.episodes, name='episodes'),
    path('characters/', views.characters_view, name='characters'),
]
