from django.urls import path, include
from episode import views

urlpatterns = [
    path('<str:nama_episode>/', views.episode_view, name='episode_detail'),
]
