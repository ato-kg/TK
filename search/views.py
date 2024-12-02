import requests
from bs4 import BeautifulSoup
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import render
from urllib.parse import quote

from rdfapp.rdf_manager import RDFManager
from rdfapp.wikidata_manager import WikidataManager
from SPARQLWrapper import JSON

rdf_manager = RDFManager()
wikidata_manager = WikidataManager()

prefix_mapping = {
    "http://example.org/data/": "ex:",
    "http://example.org/vocab#": "exv:",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf:",
    "http://www.w3.org/2000/01/rdf-schema#": "rdfs:",
    "http://www.wikidata.org/entity/": "wd:",
    "http://www.w3.org/2001/XMLSchema#": "xsd:",
}


def search(request):
    query = request.GET.get("q", "")
    more_results = False
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        results = []
        if query:
            sparql_query = f"""
PREFIX ex: <http://example.org/data/>
PREFIX exv: <http://example.org/vocab#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT DISTINCT ?subject ?name ?type
WHERE {{
    {{
        SELECT ?subject ?name ?type
        WHERE {{
            ?subject exv:name ?name .
            ?subject rdf:type ?type .
            FILTER(strStarts(lcase(?name), lcase("{query}")))
            FILTER(?type = exv:Character)
        }}
        ORDER BY ?name
    }}
    UNION
    {{
        SELECT ?subject ?name ?type
        WHERE {{
            ?subject exv:title ?name .
            ?subject rdf:type ?type .
            FILTER(strStarts(lcase(?name), lcase("{query}")))
            FILTER(?type = exv:Episode)
        }}
        ORDER BY ?name
    }}
    UNION
    {{
        SELECT ?subject ?name ?type
        WHERE {{
            ?subject exv:name ?name .
            ?subject rdf:type ?type .
            FILTER(contains(lcase(?name), lcase("{query}")) && !strStarts(lcase(?name), lcase("{query}")))
            FILTER(?type = exv:Character)
        }}
        ORDER BY ?name
    }}
    UNION
    {{
        SELECT ?subject ?name ?type
        WHERE {{
            ?subject exv:title ?name .
            ?subject rdf:type ?type .
            FILTER(contains(lcase(?name), lcase("{query}")) && !strStarts(lcase(?name), lcase("{query}")))
            FILTER(?type = exv:Episode)
        }}
        ORDER BY ?name
    }}
}}
"""
            sparql_wrapper = rdf_manager.sparql
            sparql_wrapper.setQuery(sparql_query)
            sparql_wrapper.setReturnFormat(JSON)
            response = sparql_wrapper.query()
            # print("gyatt")
            # print(response)
            # print("gyatt")
            bindings = response.convert()["results"]["bindings"]
            # print("gyatt")
            # print(bindings)
            # print("gyatt")
            # if len(bindings) > 10:
            #     more_results = True
            #     bindings = bindings[:10]
            subject_dict = {}
            for binding in bindings:
                subject_uri = binding["subject"]["value"]
                for uri, prefix in prefix_mapping.items():
                    if subject_uri.startswith(uri):
                        subject_prefixed = subject_uri.replace(uri, prefix)
                        break
                else:
                    subject_prefixed = subject_uri

                result_type = binding["type"]["value"]
                if result_type.startswith("http://example.org/vocab#"):
                    result_type = result_type.replace("http://example.org/vocab#", "")
                name = binding["name"]["value"]
                # url = binding["url"]["value"]

                if subject_prefixed not in subject_dict:
                    subject_dict[subject_prefixed] = {}
                    subject_dict[subject_prefixed][result_type] = [name]
                else:
                    if result_type not in subject_dict[subject_prefixed]:
                        subject_dict[subject_prefixed][result_type] = [name]
                    else:
                        subject_dict[subject_prefixed][result_type].append(name)

            # print("gyatt")
            # print(subject_dict)
            # print("gyatt")

            for subject, types in subject_dict.items():
                for result_type, names in types.items():
                    for name in names:
                        encoded_name = quote(name)
                        if result_type == "Character":
                            relative_url = f"/character/{encoded_name}/"
                        elif result_type == "Episode":
                            relative_url = f"/episode/{encoded_name}/"

                        results.append(
                            {
                                "subject": subject,
                                "name": name,
                                "url": relative_url,
                                "type": result_type,
                            }
                        )
            print(results)
        return JsonResponse({"results": results, "more_results": more_results})
    context = {"query": query, "results": []}

    return render(request, "home.html", context)


def episodes(request):
    query = request.GET.get("q", "")
    season = request.GET.get("season", "")
    sort = request.GET.get("sort", "title-asc")

    sparql_query = f"""
    PREFIX ex: <http://example.org/data/>
    PREFIX exv: <http://example.org/vocab#>

    SELECT ?episode ?title ?season ?views ?episode_number
    WHERE {{
        ?episode exv:title ?title .
                 OPTIONAL {{ ?episode exv:isSeasonNo ?season }} .
                 OPTIONAL {{ ?episode exv:hasViewers ?views }} .
                 OPTIONAL {{ ?episode exv:isEpisodeNo ?episode_number }} .
        FILTER(contains(lcase(?title), lcase("{query}")))
        {f"FILTER(?season = '{season}')" if season else ""}
    }}
    ORDER BY {"ASC(?views)" if sort == "views-asc" else "DESC(?views)" if sort == "views-desc" else ""}
             {"ASC(?title)" if sort == "title-asc" else "DESC(?title)" if sort == "title-desc" else ""}
             {"ASC(?episode_number)" if sort == "episode-number-asc" else "DESC(?episode_number)" if sort == "episode-number-desc" else ""}
    """
    sparql_wrapper = rdf_manager.sparql
    sparql_wrapper.setQuery(sparql_query)
    sparql_wrapper.setReturnFormat(JSON)
    response = sparql_wrapper.query()
    bindings = response.convert()["results"]["bindings"]
    print(bindings)
    print("gyatt")

    episodes = [
        {
            "title": binding["title"]["value"],
            "season": binding.get("season", {}).get("value", "N/A"),
            "views": binding.get("views", {}).get("value", "N/A"),
            "episode_number": binding.get("episode_number", {}).get("value", "N/A"),
            "imdb_rating": get_imdb_rating(binding["title"]["value"]),
            "url": f"/episode/{quote(binding['title']['value'])}/",
            "image": get_image("https://spongebob.fandom.com/wiki/" + binding["title"]["value"]),
        }
        for binding in bindings
    ]
    print(episodes)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"episodes": episodes})

    context = {"query": query, "results": episodes}
    return render(request, "episodes.html", context)


def get_imdb_rating(nama_episode):
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
    params = {"title": nama_episode}
    results = rdf_manager.query(sparql_query, params)
    if results:
        eps_uri = results[0]['s']['value']
        eps_wd = get_attribute(eps_uri, "hasWikidata")
        if eps_wd:
            results = wikidata_manager.get_attribute(eps_wd, "http://www.wikidata.org/prop/direct/P345")
            if not results:
                results = wikidata_manager.get_attribute(eps_wd, "http://www.wikidata.org/prop/direct/P361")
                if results:
                    full_eps_wd = results[0]['object']['value']
                    results = wikidata_manager.get_attribute(full_eps_wd, "http://www.wikidata.org/prop/direct/P345")
            if results:
                imdb_id = results[0]['object']['value']
                url = f"https://www.imdb.com/title/{imdb_id}/"
                return get_imdb_rating_from_url(url)
    return "Rating not found"

def get_imdb_rating_from_url(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        rating_tag = soup.find('span', class_='sc-d541859f-1 imUuxf')
        if rating_tag:
            return rating_tag.text
    return "Rating not found"


def get_attribute(s_uri, atr):
    if s_uri is None:
        return None
    sparql_query = f"""
    PREFIX exv: <http://example.org/vocab#>

    SELECT ?o
    WHERE {{
        <{s_uri}> exv:{atr} ?o .
    }}
    LIMIT 1
    """
    results = rdf_manager.query(sparql_query)
    if results:
        return results[0]["o"]["value"]
    else:
        return None

def get_image(fandom_url):
    try:
        response = requests.get(fandom_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        infobox_image = soup.select_one(".pi-image-thumbnail")
        if infobox_image:
            image_url = infobox_image['src']
            return image_url
        else:
            return None
    except:
        return None