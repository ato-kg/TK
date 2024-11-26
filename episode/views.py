import requests
from bs4 import BeautifulSoup
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import render

from rdfapp.rdf_manager import RDFManager
from rdfapp.wikidata_manager import WikidataManager

rdf_manager = RDFManager()
wikidata_manager = WikidataManager()


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

def episode_view(request, nama_episode : str):
    print(nama_episode)
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
    context = {}
    results = rdf_manager.query(sparql_query, params)
    if results:
        eps_uri = results[0]['s']['value']
        eps_wd = get_attribute(eps_uri, "hasWikidata")
        print(eps_wd)
        
        results = wikidata_manager.get_attribute(eps_wd, "http://www.wikidata.org/prop/direct/P345")
        if not results:
            results = wikidata_manager.get_attribute(eps_wd, "http://www.wikidata.org/prop/direct/P361")
            if results:
                full_eps_wd = results[0]['object']['value']
                print(full_eps_wd)
                results = wikidata_manager.get_attribute(full_eps_wd, "http://www.wikidata.org/prop/direct/P345")
        if results:
            imdb_id = results[0]['object']['value']
            imdb_url = f"https://www.imdb.com/title/{imdb_id}/"
        else:
            imdb_id = None
            imdb_url = None
        rating = get_imdb_rating(imdb_id)
        print(f"IMDb Rating for {imdb_id}: {rating}")

        url = "https://spongebob.fandom.com/wiki/" + nama_episode.replace(" ", "_")
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        infobox_image = soup.select_one(".pi-image-thumbnail")
        image_url = None
        if infobox_image:
            image_url = infobox_image['src']
            print("URL Gambar:", image_url)
        else:
            print("Gambar tidak ditemukan di infobox.")
        context['image_url'] = image_url
        context['imdb_url'] = imdb_url
        context['rating'] = rating
        return render(request, 'template.html', context)
    else:
        return HttpResponseNotFound(f"Episode '{nama_episode}' tidak ditemukan.")


def get_imdb_rating(imdb_id):
    api_key = "fd083948"  # API key Anda
    url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={api_key}"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if "imdbRating" in data:
            return data["imdbRating"]
        else:
            return "Rating not found"
    else:
        return f"Error: {response.status_code}"

