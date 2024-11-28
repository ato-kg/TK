from django.urls import path
from gallery.views import gallery_episode_view, gallery_char_view

urlpatterns = [
    path('episode/<str:nama_episode>/', gallery_episode_view, name='gallery_episode'),
    path('character/<str:nama_karakter>/', gallery_char_view, name='gallery_char'),
]