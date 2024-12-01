from django.urls import path, include
from webpage import views

urlpatterns = [
    # path('', views.home, name='home'),
    # path('character/<str:name>/', views.character_detail, name='character_detail'),
    path('detail/episode/<str:nama_episode>/', views.webpage_episode_detail_view, name='webpage_episode_detail'),
]
