import requests
from bs4 import BeautifulSoup
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import render

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

SELECT ?subject ?name ?url
            WHERE {{
                ?subject exv:name ?name .
                OPTIONAL {{ ?subject ?p ?url . }}
                FILTER(contains(lcase(?name), lcase("{query}")))
            }}
LIMIT 10
"""
            sparql_wrapper = rdf_manager.sparql
            sparql_wrapper.setQuery(sparql_query)
            sparql_wrapper.setReturnFormat(JSON)
            response = sparql_wrapper.query()
            # print("gyatt")
            # print(response)
            # print("gyatt")
            bindings = response.convert()["results"]["bindings"]
            print("gyatt")
            print(bindings)
            print("gyatt")
            for binding in bindings:
                subject_uri = binding['name']['value']
                for uri, prefix in prefix_mapping.items():
                    if subject_uri.startswith(uri):
                        subject_prefixed = subject_uri.replace(uri, prefix)
                        break
                else:
                    subject_prefixed = subject_uri
                
                results.append({
                    'name': subject_prefixed,
                    'url': binding['url']['value'],
                })
        return JsonResponse({"results": results})
    context = {"query": query, "results": []}

    return render(request, "search.html", context)
