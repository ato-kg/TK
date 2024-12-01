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