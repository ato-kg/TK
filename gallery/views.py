import requests
import re

from bs4 import BeautifulSoup
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import render

from rdfapp.rdf_manager import RDFManager
from rdfapp.wikidata_manager import WikidataManager
from urllib.parse import urlparse, parse_qs
from pytubefix import YouTube

rdf_manager = RDFManager()
wikidata_manager = WikidataManager()

### LOGIC ###

def get_attribute(eps_uri, atr):
    sparql_query = f"""
    PREFIX exv: <http://example.org/vocab#>

    SELECT ?o
    WHERE {{
        <{eps_uri}> exv:{atr} ?o .
    }}
    LIMIT 1
    """
    results = rdf_manager.query(sparql_query)
    if results:
        return results[0]['o']['value']
    return None

def get_eps_fandom_page(nama_episode : str):
    sparql_query = f"""
    PREFIX exv: <http://example.org/vocab#>
    
    SELECT ?s
    WHERE {{
        ?s a exv:Episode ;
            exv:title ?o .
        FILTER(?o = ?title)
    }}
    LIMIT 1
    """
    params = {
        "title": nama_episode
    }
    
    results = rdf_manager.query(sparql_query, params)
    if results:
        eps_uri = results[0]['s']['value']
        if not eps_uri:
            return None
        eps_fandom = get_attribute(eps_uri, "hasUrlEps")
        
        if eps_fandom:
            fandom_page = eps_fandom 
        else:
            fandom_page = None
    
        return fandom_page
    
    return None

def get_freebase_id_character(nama_karakter : str):
    sparql_query = f"""
    PREFIX exv: <http://example.org/vocab#>
    
    SELECT ?s
    WHERE {{
        ?s a exv:Character ;
            exv:name ?o .
        FILTER(?o = ?name)
    }}
    LIMIT 1
    """
    params = {
        "name": nama_karakter
    }
    
    results = rdf_manager.query(sparql_query, params)
    if results:
        char_uri = results[0]['s']['value']
        if not char_uri:
            return None
        char_wd = get_attribute(char_uri, "hasWikidata")

        if char_wd:
            results = wikidata_manager.get_attribute(char_wd, "http://www.wikidata.org/prop/direct/P646")

            if results:
                return results[0]['object']['value']
            else:
                return None
        else:
            return None
        
    return None

def get_freebase_id_episode(nama_episode : str):
    sparql_query = f"""
    PREFIX exv: <http://example.org/vocab#>
    
    SELECT ?s
    WHERE {{
        ?s a exv:Episode ;
            exv:title ?o .
        FILTER(?o = ?title)
    }}
    LIMIT 1
    """
    params = {
        "title": nama_episode
    }
    
    results = rdf_manager.query(sparql_query, params)
    if results:
        eps_uri = results[0]['s']['value']
        if not eps_uri:
            return None
        eps_wd = get_attribute(eps_uri, "hasWikidata")
        
        if eps_wd:
            results = wikidata_manager.get_attribute(eps_wd, "http://www.wikidata.org/prop/direct/P646")
            
            if results:
                return results[0]['object']['value']
            else:
                return None
        else:
            return None
        
    return None

def extract_youtube_link(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    video_link = query_params.get('imgrefurl', [None])[0]

    if video_link is None:
        video_link = query_params.get('q', [None])[0]
    if video_link:
        return video_link
    return None

def get_images_eps_caption(fandom_page):
    if fandom_page:
        response = requests.get(fandom_page)
        soup = BeautifulSoup(response.content, 'html.parser')
        all_figures = soup.find_all('figure', {'class':'thumb tright show-info-icon'})
        
        images = []
        for figure in all_figures:
            a_element = figure.find('a', recursive=False)
            img_element = a_element.find('img', recursive=False)
            img_src = img_element['data-src']
            caption = figure.find('p', {'class':'caption'})

            if caption:
                caption = caption.text
            else:
                caption = ""
            img_src = img_src.split("/revision/latest/")[0]

            data_image = {
                "link": img_src,
                "caption": caption
            }

            images.append(data_image)
            
        return images
    else:
        return None

def get_char_fandom_page(nama_karakter : str):
    sparql_query = f"""
    PREFIX exv: <http://example.org/vocab#>
    
    SELECT ?s
    WHERE {{
        ?s a exv:Character ;
            exv:name ?o .
        FILTER(?o = ?name)
    }}
    LIMIT 1
    """
    params = {
        "name": nama_karakter
    }
    
    results = rdf_manager.query(sparql_query, params)
    if results:
        char_uri = results[0]['s']['value']
        if not char_uri:
            return None
        results = get_attribute(char_uri, "hasUrl")
        
        if results:
            fandom_page = results + "/gallery"
        else:
            fandom_page = None
    
        return fandom_page
    
    return None

def get_images_char_caption(fandom_page : str):
    if fandom_page:
        try:
            response = requests.get(fandom_page)
            soup = BeautifulSoup(response.content, 'html.parser')
            gallery = soup.find('div', {'id': 'gallery-0'})
            gallery_item = gallery.find_all('div', {'class': 'wikia-gallery-item'}, recursive=False)
        except:
            fandom_page = fandom_page.replace("/gallery", "")
            response = requests.get(fandom_page)
            soup = BeautifulSoup(response.content, 'html.parser')
            gallery = soup.find('div', {'id': 'gallery-0'})
            if not gallery:
                return None
            gallery_item = gallery.find_all('div', {'class': 'wikia-gallery-item'}, recursive=False)

        images = []
        for item in gallery_item:
            a_element = item.find('a', {'class': 'image lightbox'})
            img_element = a_element.find('img', recursive=False)
            img_src = img_element['data-src']
            img_name = img_element['alt']
            img_src = img_src.split("/revision/latest/")[0]
            
            data_image = {
                "link": img_src,
                "caption": img_name
            }
            images.append(data_image)
            
        return images
    else:
        return None
    
def get_related_video(freebase_id):
    response = requests.get(f"https://www.google.com/search?kgmid={freebase_id}")
    soup = BeautifulSoup(response.content, 'html.parser')

    data = []
    for link in soup.find_all('a'):
        if "youtube.com/watch" in link['href']:
            video_link = link['href']
            video_link = extract_youtube_link(video_link)
            if not video_link:
                continue
            if any(d['link'] == video_link for d in data):
                continue
        
            yt = YouTube(video_link)
            video_title = yt.title
            video_thumbnail = yt.thumbnail_url

            data_video = {
                "link": video_link,
                "title": video_title,
                "thumbnail": video_thumbnail,
                "embed_url": video_link.replace("watch?v=", "embed/")
            }
            data.append(data_video)
        
    return data
    

### VIEWS ###

def gallery_episode_view(request, nama_episode : str):
    fandom_page = get_eps_fandom_page(nama_episode)
    images = get_images_eps_caption(fandom_page)
    freebase_id = get_freebase_id_episode(nama_episode)
    related_video = []
    if freebase_id:
        related_video = get_related_video(freebase_id)
    
    if images:
        context = {
            'nama_episode': nama_episode,
            'images': images,
            'videos': related_video
        }
        return render(request, 'galleryEpisode.html', context)
    else:
        return HttpResponseNotFound("Episode does not have images")

def gallery_char_view(request, nama_karakter : str):
    fandom_page = get_char_fandom_page(nama_karakter)
    images = get_images_char_caption(fandom_page)
    freebase_char = get_freebase_id_character(nama_karakter)
    related_video = []
    if freebase_char:
        related_video = get_related_video(freebase_char)
    
    if images:
        context = {
            'nama_karakter': nama_karakter,
            'images': images,
            'videos': related_video
        }
        return render(request, 'galleryCharacter.html', context)
    else:
        return HttpResponseNotFound("Character does not have images")