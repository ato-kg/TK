from django.urls import path, include
from episode import views  # Ganti 'episode' dengan nama aplikasi Anda

urlpatterns = [
    path('<str:nama_episode>/', views.episode_view, name='episode_detail'),
]
