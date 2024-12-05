from django.urls import include, path

from episode import views

urlpatterns = [
    path('<str:nama_episode>/', views.episode_view, name='episode_detail'),
    path('get-summary/<str:page_title>/', views.get_summary_view, name='get_summary'),
    path('get-synopsis/<str:page_title>/', views.get_synopsis_view, name='get_synopsis'),
]
