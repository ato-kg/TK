from django.urls import path, include
from character import views

urlpatterns = [
    path('<str:nama_character>/', views.character_view, name='character_detail'),
    path('get-summary/<str:page_title>/', views.get_summary_view, name='get_summary'),
    path('get-synopsis/<str:page_title>/', views.get_synopsis_view, name='get_synopsis'),
]
