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

SPARQL_PREFIXES = """
PREFIX ex: <http://example.org/data/>
PREFIX exv: <http://example.org/vocab#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""


def search(request):
    query = request.GET.get("q", "")
    more_results = False
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        results = []
        if query:
            sparql_query = f"""
{SPARQL_PREFIXES}

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
    query = f"""
    {SPARQL_PREFIXES}
    SELECT DISTINCT ?season
    WHERE {{
        ?episode exv:isSeasonNo ?season
    }}
    ORDER BY ASC(?season)
    """
    return query


def getQueryEpisodeList(query, season, sort):
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
    elif sort == "imdb-rating-asc":
        order_by_clause = "ORDER BY ASC(?imdb_rating)"
    elif sort == "imdb-rating-desc":
        order_by_clause = "ORDER BY DESC(?imdb_rating)"
    

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
    {SPARQL_PREFIXES}
    SELECT distinct ?episode ?title ?season ?views ?episode_number ?image_url ?imdb_rating
    WHERE {{
        ?episode exv:title ?title .
        ?episode a exv:Episode .
        OPTIONAL {{ ?episode exv:isSeasonNo ?season }} .
        OPTIONAL {{ ?episode exv:hasViewers ?views }} .
        OPTIONAL {{ ?episode exv:isEpisodeNo ?episode_number }} .
        OPTIONAL {{ ?episode exv:hasImageEps ?image_url }} .
        OPTIONAL {{ ?episode exv:hasRating ?imdb_rating }} .
        FILTER(contains(lcase(?title), lcase("{query}")))
        {season_filter}
    }}
    {order_by_clause}
    """
    return query


def natural_sort_key(episode_number, reverse=False):
    if episode_number == "N/A" or episode_number is None:
        return (
            (float("-inf"), "") if not reverse else (float("inf"), "")
        )  # Treat N/A or missing as smallest for asc, largest for desc
    match = re.match(r"(\d+)([a-zA-Z\-]*)", episode_number)
    if match:
        number = int(match.group(1))
        suffix = match.group(2)
        return (number, suffix)
    return (
        (float("-inf"), "") if not reverse else (float("inf"), "")
    )  # Fallback for unexpected formats


def episodes(request):
    query = request.GET.get("q", "")
    season = request.GET.get("season", "")
    sort = request.GET.get("sort", "title-asc")
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 18))

    unique_seasons_query = getUniqueSeasonsQuery()
    seasons_response = rdf_manager.query(unique_seasons_query)
    unique_seasons = [binding.get("season", {}).get("value", "N/A") for binding in seasons_response]

    sparql_query = getQueryEpisodeList(query, season, sort)
    response = rdf_manager.query(sparql_query)
    episodes = [
        {
            "episode_uri": binding["episode"]["value"],
            "title": binding["title"]["value"],
            "season": binding.get("season", {}).get("value", "N/A"),
            "views": binding.get("views", {}).get("value", "N/A"),
            "episode_number": binding.get("episode_number", {}).get("value", "N/A"),
            "imdb_rating": binding.get("imdb_rating", {}).get("value", "N/A"),
            "url": f"/episode/{quote(binding['title']['value'])}/",
            "image": binding.get("image_url", {}).get("value", "N/A"),
        }
        for binding in response
    ]
    if "episode-number" in sort:
        reverse_sort = sort == "episode-number-desc"
        episodes.sort(key=lambda ep: natural_sort_key(ep["episode_number"]), reverse=reverse_sort)

    paginator = Paginator(episodes, page_size)
    paginated_episodes = paginator.get_page(page)
    print(paginator.count)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "episodes": list(paginated_episodes),
            "page": page,
            "page_size": page_size,
            "total_episodes": paginator.count
        })

    context = {
        "query": query,
        "results": paginated_episodes,
        "unique_seasons": unique_seasons,
    }
    return render(request, "episodes.html", context)


def characters_view(request):
    query = request.GET.get("q", "")
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 18))

    sparql_query = f"""
    {SPARQL_PREFIXES}

    SELECT DISTINCT ?character ?name ?image_url
    WHERE {{
        {{
            SELECT ?character ?name ?image_url
            WHERE {{
                ?character exv:name ?name .
                ?character a exv:Character .
                OPTIONAL {{ ?character exv:hasImageChar ?image_url }} .
                FILTER(strStarts(lcase(?name), lcase("{query}")))
                FILTER NOT EXISTS {{
                    ?character rdf:type ?teamRole .
                    ?teamRole rdfs:subClassOf exv:TeamProduction .
                }}
            }}
            ORDER BY ?name
        }}
        UNION
        {{
            SELECT ?character ?name ?image_url
            WHERE {{
                ?character exv:name ?name .
                ?character a exv:Character .
                OPTIONAL {{ ?character exv:hasImageChar ?image_url }} .
                FILTER(contains(lcase(?name), lcase("{query}")) && !strStarts(lcase(?name), lcase("{query}")))
                FILTER NOT EXISTS {{
                    ?character rdf:type ?teamRole .
                    ?teamRole rdfs:subClassOf exv:TeamProduction .
                }}
            }}
            ORDER BY ?name
        }}
    }}
    """

    results = rdf_manager.query(sparql_query)
    characters = []
    for result in results:
        character = {
            "name": result["name"]["value"],
            "image_url": result.get("image_url", {}).get("value", "N/A"),
            "url": f"/character/{quote(result['name']['value'])}/",
        }
        characters.append(character)

    paginator = Paginator(characters, page_size)
    paginated_characters = paginator.get_page(page)
    print(paginator.count)

    data = {
        "characters": list(paginated_characters),
        "page": page,
        "total_characters": paginator.count,
    }
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(data)

    context = {
        "query": query,
        "results": paginated_characters,
    }
    return render(request, "characters.html", context)