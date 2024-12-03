import re
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from django.core.paginator import Paginator
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import render
from SPARQLWrapper import JSON

from rdfapp.rdf_manager import RDFManager
from rdfapp.wikidata_manager import WikidataManager

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
            # print(results)
        return JsonResponse({"results": results, "more_results": more_results})
    context = {"query": query, "results": []}

    return render(request, "home.html", context)

def getUniqueSeasonsQuery():
    query = """
    PREFIX ex: <http://example.org/data/>
    PREFIX exv: <http://example.org/vocab#>

    SELECT DISTINCT ?season
    WHERE {
        OPTIONAL { ?episode exv:isSeasonNo ?season }
    }
    ORDER BY ASC(?season)
    """
    return query

def getQueryEpisodeList(query, season, sort, page, page_size, total: bool):
    if total:
        column = "(COUNT(?episode) as ?total)"
        limitpage = ""
    else:
        column = "?episode ?title ?season ?views ?episode_number ?image_url"
        limitpage = ""
    
    order_by_clause = ""
    if sort == "views-asc":
        order_by_clause = """
        ORDER BY ASC(
            IF(
                contains(?views, 'N/A') || contains(?views, 'TBD'), 
                "0", 
                ?views
            )
        )
        """
    elif sort == "views-desc":
        order_by_clause = """
        ORDER BY DESC(
            IF(
                contains(?views, 'N/A') || contains(?views, 'TBD'), 
                "0", 
                ?views
            )
        )
        """
    elif sort == "title-asc":
        order_by_clause = "ORDER BY ASC(?title)"
    elif sort == "title-desc":
        order_by_clause = "ORDER BY DESC(?title)"
    elif sort == "episode-number-asc" or sort == "episode-number-desc":
        order_by_clause = ""

    season_filter = ""
    if season:
        if season == "N/A":
            season_filter = "FILTER(!BOUND(?season))"
        else:
            try:
                season_number = int(season)
                season_filter = f"FILTER(xsd:integer(?season) = {season_number})"
            except ValueError:
                season_filter = f"FILTER(?season = '{season}')"

    query = f"""
    PREFIX ex: <http://example.org/data/>
    PREFIX exv: <http://example.org/vocab#>

    SELECT {column}
    WHERE {{
        ?episode exv:title ?title .
        OPTIONAL {{ ?episode exv:isSeasonNo ?season }} .
        OPTIONAL {{ ?episode exv:hasViewers ?views }} .
        OPTIONAL {{ ?episode exv:isEpisodeNo ?episode_number }} .
        OPTIONAL {{ ?episode exv:hasImageEps ?image_url }} .
        FILTER(contains(lcase(?title), lcase("{query}")))
        {season_filter}
    }}
    {order_by_clause}
    {limitpage}
    """
    return query

def natural_sort_key(episode_number, reverse=False):
    if episode_number == "N/A" or episode_number is None:
        return (float('-inf'), '') if not reverse else (float('inf'), '')  # Treat N/A or missing as smallest for asc, largest for desc
    match = re.match(r"(\d+)([a-zA-Z\-]*)", episode_number)
    if match:
        number = int(match.group(1))
        suffix = match.group(2)
        return (number, suffix)
    return (float('-inf'), '') if not reverse else (float('inf'), '')  # Fallback for unexpected formats

def episodes(request):
    query = request.GET.get("q", "")
    season = request.GET.get("season", "")
    sort = request.GET.get("sort", "title-asc")
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 18))
    # print(type(season))

    unique_seasons_query = getUniqueSeasonsQuery()
    sparql_wrapper = rdf_manager.sparql
    sparql_wrapper.setQuery(unique_seasons_query)
    sparql_wrapper.setReturnFormat(JSON)
    seasons_response = sparql_wrapper.query()
    seasons_bindings = seasons_response.convert()["results"]["bindings"]
    unique_seasons = [binding.get("season", {}).get("value", "N/A") for binding in seasons_bindings]

    count_query = getQueryEpisodeList(query, season, sort, page, page_size, total=True)
    sparql_wrapper.setQuery(count_query)
    sparql_wrapper.setReturnFormat(JSON)
    count_response = sparql_wrapper.query()
    total_episodes = int(count_response.convert()["results"]["bindings"][0]["total"]["value"])
    print(total_episodes)

    sparql_query = getQueryEpisodeList(query, season, sort, page, page_size, total=False)
    sparql_wrapper.setQuery(sparql_query)
    sparql_wrapper.setReturnFormat(JSON)
    response = sparql_wrapper.query()
    bindings = response.convert()["results"]["bindings"]
    # print(bindings)
    # print("gyatt")

    episodes = [
        {
            "title": binding["title"]["value"],
            "season": binding.get("season", {}).get("value", "N/A"),
            "views": binding.get("views", {}).get("value", "N/A"),
            "episode_number": binding.get("episode_number", {}).get("value", "N/A"),
            # "imdb_rating": get_imdb_rating(binding["title"]["value"]), #TODO
            "url": f"/episode/{quote(binding['title']['value'])}/",
            "image": binding.get("image_url", {}).get("value", "N/A"),
        }
        for binding in bindings
    ]
    if "episode-number" in sort:
        reverse_sort = sort == "episode-number-desc"
        episodes.sort(key=lambda ep: natural_sort_key(ep["episode_number"]), reverse=reverse_sort)
    # print(episodes)

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_episodes = episodes[start_idx:end_idx]


    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "episodes": paginated_episodes,
            "page": page,
            "page_size": page_size,
            "total_episodes": total_episodes
        })

    # Render the page normally
    context = {
        "query": query,
        "results": paginated_episodes,
        "unique_seasons": unique_seasons,
    }
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