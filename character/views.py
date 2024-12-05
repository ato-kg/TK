import urllib.parse

import fandom
import requests
from bs4 import BeautifulSoup
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import render

from rdfapp.rdf_manager import RDFManager
from rdfapp.wikidata_manager import WikidataManager

rdf_manager = RDFManager()
wikidata_manager = WikidataManager()
fandom.set_wiki("spongebob")

def get_attribute_rdfs(s_uri, atr):
    if s_uri is None:
        return None

    # Ensure the attribute is valid for the RDFS query.
    if not atr:
        return None
    
    sparql_query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?o
    WHERE {{
        <{s_uri}> rdfs:{atr} ?o .
    }}
    LIMIT 1
    """
    
    # Debugging: Print the generated query
    # print(f"Generated SPARQL Query: {sparql_query}")  # Print the SPARQL query for debugging
    
    try:
        # Execute the SPARQL query
        results = rdf_manager.query(sparql_query)
        
        # Check if there are results
        if results:
            # print(f"Query results: {results}")
            return results[0]['o']['value']
        else:
            # print(f"No results found for {decoded_uri} with attribute {atr}")
            return None
    except Exception as e:
        # Print the error for debugging if the query fails
        # print(f"Error executing SPARQL query: {e}")
        return None


    
def get_attribute(s_uri, atr):
    if s_uri is None or not s_uri.strip():
        return None
    sparql_query = f"""
    PREFIX exv: <http://example.org/vocab#>

    SELECT ?o
    WHERE {{
        <{s_uri}> exv:{atr} ?o .
    }}
    LIMIT 1
    """
    
    # # print(f"SPARQL Query: {sparql_query}")  # Debugging output for query
    
    try:
        results = rdf_manager.query(sparql_query)
        if results:
            return results[0]['o']['value']
        else:
            return None
    except Exception as e:
        # # print(f"Error querying SPARQL endpoint: {e}")  # Log the error
        return None


def get_attributes(s_uri, atr):
    if s_uri is None:
        return None
    sparql_query = f"""
    PREFIX exv: <http://example.org/vocab#>

    SELECT ?o
    WHERE {{
        <{s_uri}> exv:{atr} ?o .
    }}
    """
    val = []
    results = rdf_manager.query(sparql_query)
    for result in results:
        val.append(result['o']['value'])
    return val

def get_atrributes_bn(s_uri, atr, atr1, atr2):
    if s_uri is None:
        return None, {}

    sparql_query = f"""
    PREFIX exv: <http://example.org/vocab#>

    SELECT ?o1 ?o2
    WHERE {{
        <{s_uri}> exv:{atr} ?bn .
        ?bn exv:{atr1} ?o1 .
        OPTIONAL {{ ?bn exv:{atr2} ?o2 . }}
    }}
    """
    atr_main = []
    atr_info = {}

    # Execute the SPARQL query and iterate through results
    results = rdf_manager.query(sparql_query)
    for result in results:
        o1 = result['o1']['value']

        # Check if 'o2' exists (i.e., is part of the result)
        o2 = result.get('o2', {}).get('value', None)

        # # If 'o2' is not present, set it to None or some default value
        if o2 is None:
            o2 = "No additional information"  # You can change this message to something else if needed

        # Add the main object (o1) to the list if not already added
        if o1 not in atr_main:
            atr_main.append(o1)
            atr_info[o1] = []

        # Add the secondary object (o2) to the dictionary (if not already present)
        if o2 not in atr_info[o1]:
            atr_info[o1].append(o2)

    return atr_main, atr_info

def get_exv_classifications(character_uri):
    # SPARQL query to fetch all types associated with the character, excluding `exv:Character`
    query = f"""
    PREFIX ex: <http://example.org/data/>
    PREFIX exv: <http://example.org/vocab#>

    SELECT ?type
    WHERE {{
      <{character_uri}> a ?type .
      FILTER (?type != exv:Character)
    }}
    """
    
    # Execute the query using your RDF manager (assuming you have an RDF graph)
    results = rdf_manager.query(query)
    
    # Collect all the URIs of types (excluding `exv:Character`)
    exv_types = []
    for row in results:
        exv_types.append(row["type"])  # Convert each URI to string
    
    return exv_types

def character_view(request, nama_character : str):
    print(1)
    print(nama_character)
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
        "name": nama_character
    }
    context = {'name' : nama_character}
    results = rdf_manager.query(sparql_query, params)
    if results:
        print(2)
        char_uri = results[0]['s']['value']
        
        # WikiData
        char_wd = get_attribute(char_uri, "hasWikidata")
        context['char_wd'] = char_wd

        # Appear In Checked
        appeared_in_url = get_attribute(char_uri, "appearIn")
        appeared_in = get_attribute(appeared_in_url, "title")
        context['appeared_in'] = appeared_in

        # Name Checked
        name = get_attribute(char_uri, "name")
        context['name'] = name

        # Classifications
        classifications_uri = get_exv_classifications(char_uri)
        classifications = []
        for classification_uri in classifications_uri:
            # # print(f"Processing classification URI: {classification_uri}")
            classification_uri_value = classification_uri.get("value")
            classification_name = get_attribute_rdfs(classification_uri_value, "label")
            classifications.append({
                "name": classification_name
            })
        context['classifications'] = classifications
        # # print(classifications)

        # Portrayers Checked
        portrayers = []
        portrayer_uris, portrayer_info_str = get_atrributes_bn(char_uri, "hasPortrayers", "hasPortrayer", "infoPortrayer")
        for portrayer_uri in portrayer_uris:
            portrayer_name = get_attribute(portrayer_uri, "name")
            infos =  portrayer_info_str.get(portrayer_uri)
            portrayers.append({
                "name" : portrayer_name,
                "infos" : infos,
                "uri" : portrayer_uri
            })
        context['portrayers'] = portrayers

        # Residences Checked
        residences = []
        residence_uris, residence_info_str = get_atrributes_bn(char_uri, "hasResidences", "hasResidence", "infoResidence")

        for residence_uri in residence_uris:
            # print(f"Processing residence URI: {residence_uri}")
            
            residence_name = get_attribute_rdfs(residence_uri, "label")

            if residence_name:
                infos = residence_info_str.get(residence_uri, "No info available")
                residences.append({
                    "name": residence_name,
                    "infos": infos
                })

        context['residences'] = residences

        # Spouses Checked
        spouses = []
        spouse_uris, spouse_info_str = get_atrributes_bn(char_uri, "hasSpouses", "hasSpouse", "infoSpouse")
        for spouse_uri in spouse_uris:
            spouse_name = get_attribute(spouse_uri, "name")
            infos =  spouse_info_str[spouse_uri]
            spouses.append({
                "name" : spouse_name,
                "uri" : spouse_uri,
                "infos" : infos
            })
        context['spouses'] = spouses

        # Childs Checked
        childs = []
        child_uris, child_info_str = get_atrributes_bn(char_uri, "child", "hasChild", "hasChildInfo")
        for child_uri in child_uris:
            child_name = get_attribute(child_uri, "name")
            infos =  child_info_str[child_uri]
            childs.append({
                "name" : child_name,
                "infos" : infos
            })
        context['childs'] = childs

        # Colors Checked
        colors = []
        color_strs, color_info_str = get_atrributes_bn(char_uri, "color", "hasColor", "hasColorInfo")
        for color_str in color_strs:
            infos =  color_info_str[color_str]
            colors.append({
                "name" : color_str,
                "infos" : infos
            })
        context['colors'] = colors

        # Eye Colors Checked
        eye_colors = []
        eye_color_strs, eye_color_info_strs = get_atrributes_bn(char_uri, "eyeColor", "hasEyeColor", "hasEyeColorInfo")
        for eye_color_str in eye_color_strs:
            infos =  eye_color_info_strs[eye_color_str]
            eye_colors.append({
                "name" : eye_color_str,
                "infos" : infos
            })
        context['eye_colors'] = eye_colors

        # First Appearance Checked
        first_appearance_uri = None
        first_appearance_uri, first_appearance_info_strs = get_atrributes_bn(char_uri, "firstAppearance", "hasFirstAppearance", "hasFirstAppearanceInfo")
        if first_appearance_uri:
            first_appearance_name = get_attribute(first_appearance_uri[0], "title")
            infos = first_appearance_info_strs[first_appearance_uri[0]]
            first_appearance = {
                "name" : first_appearance_name,
                "infos" : infos
            }
            context['first_appearance'] = first_appearance


        # Latest Appearance Checked
        latest_appearance_uri = None
        latest_appearance_uri, latest_appearance_info_strs = get_atrributes_bn(char_uri, "latestAppearance", "haslatestAppearance", "haslatestAppearanceInfo")
        if latest_appearance_uri:
            latest_appearance_name = get_attribute(latest_appearance_uri[0], "title")
            infos = latest_appearance_info_strs[latest_appearance_uri[0]]
            latest_appearance = {
                "name" : latest_appearance_name,
                "infos" : infos
            }
            context['latest_appearance'] = latest_appearance
            # # print(latest_appearance)

        # Gender Checked
        gender_uri = get_attribute(char_uri, "hasGender")
        gender = get_attribute(gender_uri, "gender")
        context['gender'] = gender

        # Occupations
        occupations_list = []
        occupations_uris, occupations_info_strs = get_atrributes_bn(char_uri, "hasOccupations", "occupationName", "infoOccupations")
        # # print(occupations_uris)
        # # print(occupations_info_strs)

        for occupation_uri in occupations_uris:
            infos = occupations_info_strs.get(occupation_uri, [])

            occupations_list.append({
                "name": occupation_uri,
                "infos": infos
        })
        # # print(occupations_list)
            
        # Episode
        episodes = []
        episodes_uris = find_episodes_by_character(char_uri)
        for episode_uri in episodes_uris:
            episode_name = get_attribute(episode_uri, "title")
            episode_image = get_attribute(episode_uri, "hasImageEps")
            episodes.append({
                "name": episode_name,
                "image": episode_image
            })
        context['episodes'] = episodes

        context['occupations'] = occupations_list
        print(3)
        # IMAGE Checked
        image_url = get_attribute(char_uri, "hasImageChar")
        fandom_url = get_attribute(char_uri, "hasUrl")
        context['fandom'] = fandom_url
        context['image_url'] = image_url
        # print(fandom_url)
        try:
            nama_character = fandom_url.split("https://spongebob.fandom.com/wiki/")[-1]
        except:
            pass
        # context['summary'] = get_best_summary(nama_character)

        # print(context['summary'])
        # context['biography'] = get_biography(nama_character)
        # print(context['biography'])
        # print("wpoy")
        # print(context['biography'])
        # # print(context['summary'])
        ############################################################
        return render(request, 'character_template.html', context)
    else:
        return HttpResponseNotFound(f"character '{nama_character}' tidak ditemukan.")

def get_summary_bs4(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 13_5_1 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1"
        )
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # Check if summary is inside div class="tab-line"
    tab_line_div = soup.select_one(".mw-parser-output .tab-line")
    if tab_line_div:
        paragraphs = tab_line_div.find_all("p")
        for p in paragraphs:
            if p.get_text(strip=True):
                # Remove all <sup> tags
                for sup in p.find_all("sup"):
                    sup.decompose()
                summary = p.get_text(strip=False)
                return summary
    return "Summary not found."

def get_summary_fandom(page_title):
    try:
        # print(page_title)
        page_data = fandom.page(page_title)
        # # print(page_data.content)
        return page_data.summary
    except fandom.error.PageError:
        return "Summary not found."
    
def get_best_summary(page_title, tmp):
    BASE_URL = "https://spongebob.fandom.com/wiki"
    url = f"{BASE_URL}/{page_title}"
    # print(url)

    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    # print(response.text)

    if soup.select_one(".mw-parser-output .tab-line > p"):
        print("Using BeautifulSoup approach")
        best_summary = get_summary_bs4(url)
    else:
        # print("Using Fandom API approach")
        best_summary = get_summary_fandom(page_title)

    if best_summary != "Summary not found.":
        return best_summary
    else:
        if page_title:
            return get_best_summary(tmp, "")
        return best_summary

def get_biography(nama_episode, tmp):
    try:
        page = fandom.page(nama_episode)
        data = page.content
        # print(data)
        def dfs(section):
            html = ""
            
            # Jika ada content, kita pisahkan berdasarkan paragraf
            if section['content']:
                # Pisahkan konten berdasarkan paragraf yang dipisahkan dengan '\n'
                paragraphs = section['content'].split('\n')
                for paragraph in paragraphs:
                    if paragraph.strip():  # Memastikan paragraf tidak kosong
                        html += f"<p class='mb-4'>{paragraph.strip()}</p>"
            
            # Jika ada subsections, lakukan rekursi
            if 'sections' in section:
                for sub_section in section['sections']:
                    html += f"<div class='ml-4'>"
                    html += f"<h4 class='text-xl font-semibold'>{sub_section['title']}</h4>"
                    html += dfs(sub_section)  # DFS ke sub-section
                    html += "</div>"
            
            return html
        html_content = ""
        if data.get('sections',None):
            for section in data['sections']:
                if section['title'] in ('Biography'):
                    html_content += dfs(section)  # Mulai DFS untuk bagian Biography 
        return html_content
    except Exception as e:
        if nama_episode:
            return get_biography(tmp, "")
        print(e)
        return ""

def find_episodes_by_character(character_uri):
    # print(f"Processing URI: {character_uri}")
    
    # Encode hanya bagian nama karakter, bukan seluruh URI
    base_uri = "http://example.org/data/"  # Bagian base dari URI
    character_name = character_uri.replace(base_uri, "")  # Mengambil nama karakter dari URI
    encoded_character_name = urllib.parse.quote(character_name)  # Encode hanya nama karakter

    # Buat query SPARQL dengan menggantikan encoded_character_name
    query = f"""
    PREFIX ex: <http://example.org/data/>
    PREFIX exv: <http://example.org/vocab#>
    SELECT ?episode
    WHERE {{
        ?episode a exv:Episode;
                exv:hasCharacters ex:{encoded_character_name}.
    }}
    """
    
    # Mengeksekusi query menggunakan RDFManager
    results = rdf_manager.query(query)
    
    # Mengambil hanya URI episode
    episodes = [row.get("episode").get("value") for row in results if row.get("episode")]

    return episodes


def get_summary_view(request, page_title):
    try:
        summary = ""
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
            "name": page_title
        }
        context = {'name' : page_title}
        results = rdf_manager.query(sparql_query, params)
        if results:
            print(2)
            char_uri = results[0]['s']['value']
            print(char_uri)
            fandom_url = get_attribute(char_uri, "hasUrl")
            tmp = page_title
            try:
                page_title = fandom_url.split("https://spongebob.fandom.com/wiki/")[-1]
            except:
                pass
            summary = get_best_summary(page_title, tmp)
        return JsonResponse({'summary': summary})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
def get_biography_view(request, page_title):
    try:
        biography = ""
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
            "name": page_title
        }
        context = {'name' : page_title}
        results = rdf_manager.query(sparql_query, params)
        if results:
            print(2)
            char_uri = results[0]['s']['value']
            print(char_uri)
            fandom_url = get_attribute(char_uri, "hasUrl")
            tmp = page_title
            try:
                page_title = fandom_url.split("https://spongebob.fandom.com/wiki/")[-1]
            except:
                pass
            biography = get_biography(page_title, tmp)
        return JsonResponse({'biography': biography})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
