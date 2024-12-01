from django.http import HttpResponseNotFound
from django.shortcuts import render
from django.shortcuts import get_object_or_404

from episode.views import episode_view


# Create your views here.
# def home(request):
#     # characters = Character.objects.all()[:10]  # Display top 10 characters
#     # episodes = Episode.objects.all()[:10]      # Display top 10 episodes
#     # return render(request, 'webpage/home.html', {'characters': characters, 'episodes': episodes})
#     render(request, 'home.html')

def webpage_episode_detail_view(request, nama_episode):
    # Call the episode_view to get the response and context
    response, context = episode_view(request, nama_episode)
    
    # Check if the response is a rendered template
    if isinstance(response, HttpResponseNotFound):
        return response
    
    # Render the episode_detail.html with the context
    return render(request, 'episode_detail.html', context)