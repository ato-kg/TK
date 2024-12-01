import requests
from bs4 import BeautifulSoup
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import render

from rdfapp.rdf_manager import RDFManager
from rdfapp.wikidata_manager import WikidataManager

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
    return results[0]['o']['value']

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
        eps_wd = get_attribute(eps_uri, "hasWikidata")
        
        results = wikidata_manager.get_attribute(eps_wd, "http://www.wikidata.org/prop/direct/P6262")
        spongebob_value = next(
            (item['object']['value'] for item in results 
            if item['object']['value'].startswith('spongebob:')), 
            None
        )
        
        if spongebob_value:
            fandom_page = "https://spongebob.fandom.com/wiki/" + spongebob_value.split(":")[1]
        else:
            fandom_page = None
    
        return fandom_page
    
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
        results = get_attribute(char_uri, "hasUrl")
        
        if results:
            fandom_page = results + "/gallery"
        else:
            fandom_page = None
    
        return fandom_page
    
    return None

def get_images_char_caption(fandom_page : str):
    if fandom_page:
        response = requests.get(fandom_page)
        soup = BeautifulSoup(response.content, 'html.parser')
        gallery = soup.find('div', {'id': 'gallery-0'})
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
    

### VIEWS ###

def gallery_episode_view(request, nama_episode : str):
    fandom_page = get_eps_fandom_page(nama_episode)
    images = get_images_eps_caption(fandom_page)
    
    if images:
        context = {
            'nama_episode': nama_episode,
            'images': images
        }
        return render(request, 'galleryEpisode.html', context)
    else:
        return HttpResponseNotFound("Episode does not have images")

def gallery_char_view(request, nama_karakter : str):
    fandom_page = get_char_fandom_page(nama_karakter)
    images = get_images_char_caption(fandom_page)
    
    if images:
        context = {
            'nama_karakter': nama_karakter,
            'images': images
        }
        return render(request, 'galleryCharacter.html', context)
    else:
        return HttpResponseNotFound("Character does not have images")