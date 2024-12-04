from django.urls import path, include
from character import views

urlpatterns = [
    path('<str:nama_character>/', views.character_view, name='character_detail'),
]
