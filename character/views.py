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
    if s_uri in ("http://example.org/data/bubblebuddy", "http://example.org/data/stanleys.squarepants") and atr == "hasWikidata":
        sparql_query += "\nOFFSET 0"
    results = rdf_manager.query(sparql_query)
    if results:
        return results[0]['o']['value']
    else:
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
    
    print(f"SPARQL Query: {sparql_query}")  # Debugging output for query
    
    try:
        results = rdf_manager.query(sparql_query)
        if results:
            return results[0]['o']['value']
        else:
            return None
    except Exception as e:
        print(f"Error querying SPARQL endpoint: {e}")  # Log the error
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
        return None
    sparql_query = f"""
    PREFIX exv: <http://example.org/vocab#>

    SELECT ?o1 ?o2
    WHERE {{
        <{s_uri}> exv:{atr} ?bn .
        ?bn exv:{atr1} ?o1 ;
            exv:{atr2} ?o2 .
    }}
    """
    atr_main = []
    atr_info = {}
    results = rdf_manager.query(sparql_query)
    for result in results:
        o1 = result['o1']['value']
        o2 = result['o2']['value']
        if o1 not in atr_main:
            atr_main.append(o1)
            atr_info[o1] = []
        if o2 not in atr_info[o1]:
            atr_info[o1].append(o2)

    return atr_main, atr_info

def character_view(request, nama_character : str):
    print(nama_character)
    nama_character = nama_character.replace('\\', '\\\\').replace('"', '\\"')
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
        char_uri = results[0]['s']['value']
        
        # WikiData
        char_wd = get_attribute(char_uri, "hasWikidata")
        context['char_wd'] = char_wd

        # Appear In
        appear_in_url = get_attribute(char_uri, "appearIn")
        appear_in = get_attribute(appear_in_url, "title")
        context['appear_in'] = appear_in

        # Name
        name = get_attribute(char_uri, "name")
        context['name'] = name

        # Portrayers
        portrayers = []
        portrayer_uris, portrayers_info = get_atrributes_bn(char_uri, "hasPortrayers", "hasPortrayer", "infoPortrayer")
        for portrayer_uri in portrayer_uris:
            portrayer_name = get_attribute(portrayer_uri, "hasPortrayer")
            info = []
            for portrayer_info in portrayers_info[portrayer_uri]:
                info.append(portrayer_info)
            portrayers.append({
                "potrayer" : portrayer_name,
                "info" : info
            })
        context['portrayers'] = portrayers

        # Residences
        residences = []
        residence_uris, residences_info = get_atrributes_bn(char_uri, "hasResidences", "hasResidence", "infoResidence")
        for residence_uri in residence_uris:
            residence_name = get_attribute(residence_uri, "hasResidence")
            info = []
            for residence_info in residences_info[residence_uri]:
                info.append(residence_info)
            residences.append({
                "residence" : residence_name,
                "info" : info
            })
        context['residences'] = residences

        # Spouses
        spouses = []
        spouse_uris, spouses_info = get_atrributes_bn(char_uri, "hasSpouses", "hasSpouse", "infoSpouse")
        for spouse_uri in spouse_uris:
            spouse_name = get_attribute(spouse_uri, "hasSpouse")
            info = []
            for spouse_info in spouses_info[spouse_uri]:
                info.append(spouse_info)
            spouses.append({
                "spouse" : spouse_name,
                "info" : info
            })
        context['spouses'] = spouses

        # Childs
        childs = []
        child_uris, childs_info = get_atrributes_bn(char_uri, "child", "hasChild", "hasChildInfo")
        for child_uri in child_uris:
            child_name = get_attribute(child_uri, "hasChild")
            info = []
            for child_info in childs_info[child_uri]:
                info.append(child_info)
            childs.append({
                "child" : child_name,
                "info" : info
            })
        context['childs'] = childs

        # Colors
        colors = []
        color_uris, colors_info = get_atrributes_bn(char_uri, "color", "hasColor", "hasColorInfo")
        for color_uri in color_uris:
            color_name = get_attribute(color_uri, "hasColor")
            info = []
            for color_info in colors_info[color_uri]:
                info.append(color_info)
            colors.append({
                "color" : color_name,
                "info" : info
            })
        context['colors'] = colors

        # Eye Colors
        eye_colors = []
        eye_color_uris, eye_colors_info = get_atrributes_bn(char_uri, "eyeColor", "hasEyeColor", "hasEyeColorInfo")
        for eye_color_uri in eye_color_uris:
            eye_color_name = get_attribute(eye_color_uri, "hasEyeColor")
            info = []
            for eye_color_info in eye_colors_info[eye_color_uri]:
                info.append(eye_color_info)
            eye_colors.append({
                "eye_color" : eye_color_name,
                "info" : info
            })
        context['eye_colors'] = eye_colors

        # First Appearance
        first_appearances = []
        first_appearance_uris, first_appearances_info = get_atrributes_bn(char_uri, "firstAppearance", "hasFirstAppearance", "hasFirstAppearanceInfo")
        for first_appearance_uri in first_appearance_uris:
            first_appearance_name = get_attribute(first_appearance_uri, "firstAppearance")
            info = []
            for first_appearance_info in first_appearances_info[first_appearance_uri]:
                info.append(first_appearance_info)
            first_appearances.append({
                "first_appearance" : first_appearance_name,
                "info" : info
            })
        context['first_appearances'] = first_appearances

        # Latest Appearance
        latest_appearances = []
        latest_appearances_uris, latest_appearances_info = get_atrributes_bn(char_uri, "latestAppearance", "hasLatestAppearance", "hasLatestAppearanceInfo")
        for latest_appearances_uri in latest_appearances_uris:
            latest_appearances_name = get_attribute(latest_appearances_uri, "hasLatestAppearance")
            info = []
            for latest_appearance_info in latest_appearances_info[latest_appearances_uri]:
                info.append(latest_appearance_info)
            latest_appearances.append({
                "latest_appearance" : latest_appearances_name,
                "info" : info
            })
        context['latest_appearances'] = latest_appearances

        # Genders
        genders = []
        gender_uris, genders_info = get_atrributes_bn(char_uri, "gender", "hasGender", "hasGenderInfo")
        for gender_uri in gender_uris:
            gender_name = get_attribute(gender_uri, "hasGender")
            info = []
            for gender_info in genders_info[gender_uri]:
                info.append(gender_info)
            genders.append({
                "has_gender" : gender_name,
                "info" : info
            })
        context['genders'] = genders

        # Occupations
        occupations = []
        occupation_uris, occupations_info = get_atrributes_bn(char_uri, "occupation", "hasOccupation", "hasOccupationInfo")
        for occupation_uri in occupation_uris:
            occupation_name = get_attribute(occupation_uri, "hasoccupation")
            info = []
            for occupation_info in occupations_info[occupation_uri]:
                info.append(occupation_info)
            occupations.append({
                "occupation" : occupation_name,
                "info" : info
            })
        context['occupations'] = occupations
        
        # IMAGE
        image_url = get_attribute(char_uri, "hasImageChar")
        fandom_url = get_attribute(char_uri, "hasUrl")
        context['fandom'] = fandom_url
        context['image_url'] = image_url

        context['summary'] = get_best_summary(nama_character)
        print(context['summary'])
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
        page_data = fandom.page(page_title)
        return page_data.summary
    except fandom.error.PageError:
        return "Summary not found."
    
def get_best_summary(page_title):
    BASE_URL = "https://spongebob.fandom.com/wiki"
    url = f"{BASE_URL}/{page_title}"

    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    if soup.select_one(".mw-parser-output .tab-line > p"):
        print("Using BeautifulSoup approach")
        best_summary = get_summary_bs4(url)
    else:
        print("Using Fandom API approach")
        best_summary = get_summary_fandom(page_title)

    return best_summary
