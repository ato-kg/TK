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
        sparql_query += "\nOFFSET 1"
    results = rdf_manager.query(sparql_query)
    if results:
        return results[0]['o']['value']
    else:
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
        OPTIONAL {{
            ?bn exv:{atr1} ?o1 .
        }}
        OPTIONAL {{
            ?bn exv:{atr2} ?o2 .
        }}
    }}
"""

    atr_main = []
    atr_info = {}
    results = rdf_manager.query(sparql_query)
    for result in results:
        o1 = result['o1']['value']
        o2 = None
        if 'o2' in result:
            o2 = result['o2']['value']
        if o1 not in atr_main:
            atr_main.append(o1)
            atr_info[o1] = []
        if o2 not in atr_info[o1] and o2:
            atr_info[o1].append(o2)

    return atr_main, atr_info


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
    context = {'title' : nama_episode}
    results = rdf_manager.query(sparql_query, params)
    print(5,"l")
    if results:
        eps_uri = results[0]['s']['value']
        # WD FOR IMDB
        eps_wd = get_attribute(eps_uri, "hasWikidata")
        context['eps_wd'] = eps_wd
        imdb_url = None
        imdb_id = get_attribute(eps_uri, "hasIMDB")
        # if not results:
        #     results = wikidata_manager.get_attribute(eps_wd, "http://www.wikidata.org/prop/direct/P361")
        #     if results:
        #         full_eps_wd = results[0]['object']['value']
        #         results = wikidata_manager.get_attribute(full_eps_wd, "http://www.wikidata.org/prop/direct/P345")
        print(5,"b4")
        if imdb_id:
            imdb_url = f"https://www.imdb.com/title/{imdb_id}/"
        rating = get_imdb_rating(imdb_id)
        print(5,"af")
        context['imdb_url'] = imdb_url
        context['rating'] = rating

        # Air Date
        air_date = get_attribute(eps_uri, "hasAirDate")
        context['air_date'] = air_date

        # Anim Supervisor
        animation_supervisor_uri = get_attribute(eps_uri, "hasAnimatorSupervisor")
        animation_supervisor = get_attribute(animation_supervisor_uri, "name")
        context['animation_supervisor'] = animation_supervisor

        # Creative
        creative_uri = get_attribute(eps_uri, "hasCreative")
        creative = get_attribute(creative_uri, "name")
        context['creative'] = creative

        # Episode No
        episode_no = get_attribute(eps_uri, "isEpisodeNo")
        context['episode_no'] = episode_no

        # Line Produ
        line_producer_uri = get_attribute(eps_uri, "hasLineProducer")
        line_producer = get_attribute(line_producer_uri, "name")
        context['line_producer'] = line_producer
        
        # Next Episode
        next_episode_uri = get_attribute(eps_uri, "nextEpisode")
        next_episode = get_attribute(next_episode_uri, "title")
        context['next_episode'] = next_episode
        
        # Previous Episode
        prev_episode_uri = get_attribute(eps_uri, "prevEpisode")
        prev_episode = get_attribute(prev_episode_uri, "title")
        context['prev_episode'] = prev_episode
        
        # Season No
        season_no = get_attribute(eps_uri, "isSeasonNo")
        context['season_no'] = season_no
        
        # Technical
        technical_uri = get_attribute(eps_uri, "hasTechnical")
        technical = get_attribute(technical_uri, "name")
        context['technical'] = technical
        
        # Animators
        animator_uris = get_attributes(eps_uri, "hasAnimators")
        animators = []
        for uri in animator_uris:
            animator = get_attribute(uri, "name")
            animators.append(animator)
        context['animators'] = animators

        # Characters
        character_uris = get_attributes(eps_uri, "hasCharacters")
        characters = []
        for uri in character_uris:
            character = get_attribute(uri, "name")
            character_image = get_attribute(uri, "hasImageChar")
            characters.append({
                'name': character,
                'image': character_image  # Menyimpan URL gambar
            })
        context['characters'] = characters

        # Copyright Year
        copyright_year = get_attributes(eps_uri, "hasCopyrightyear")
        context['copyright_year'] = copyright_year

        # Main Contributors
        contributor_uris = get_attributes(eps_uri, "hasMainContributors")
        contributors = []
        for uri in contributor_uris:
            contributor = get_attribute(uri, "name")
            contributors.append(contributor)
        context['contributors'] = contributors

        # Production Codes
        production_codes = get_attributes(eps_uri, "hasProductionCodes")
        context['production_codes'] = production_codes

        # Running Time
        running_time = get_attributes(eps_uri, "hasRunningTime")
        context['running_time'] = running_time

        # Sister Episodes
        sister_episode_uris = get_attributes(eps_uri, "hasSisterEpisodes")
        sister_episodes = []
        for uri in sister_episode_uris:
            sister_episode = get_attribute(uri, "title")
            sister_episodes.append(sister_episode)
        context['sister_episodes'] = sister_episodes

        # Storyboard Artists
        storyboard_artist_uris = get_attributes(eps_uri, "hasStoryboardArtists")
        storyboard_artists = []
        for uri in storyboard_artist_uris:
            storyboard_artist = get_attribute(uri, "name")
            storyboard_artists.append(storyboard_artist)
        context['storyboard_artists'] = storyboard_artists

        # Storyboard
        storyboard_uris = get_attributes(eps_uri, "hasStoryboard")
        storyboard = []
        for uri in storyboard_uris:
            storyboard_name = get_attribute(uri, "name")
            storyboard.append(storyboard_name)
        context['storyboard'] = storyboard


        # Supervising Producers
        supervising_producer_uris = get_attributes(eps_uri, "hasSupervisingProducers")
        supervising_producers = []
        for uri in supervising_producer_uris:
            supervising_producer = get_attribute(uri, "name")
            supervising_producers.append(supervising_producer)
        context['supervising_producers'] = supervising_producers

        # Supervising
        supervising_uris = get_attributes(eps_uri, "hasSupervising")
        supervising = []
        for uri in supervising_uris:
            supervising_name = get_attribute(uri, "name")
            supervising.append(supervising_name)
        context['supervising'] = supervising

        # Premier Time
        premier_time = get_attributes(eps_uri, "hasPremierTime")
        context['premier_time'] = premier_time

        # Viewers
        viewers = get_attributes(eps_uri, "hasViewers")
        context['viewers'] = viewers

        # Writers
        writer_uris = get_attributes(eps_uri, "hasWriters")
        writers = []
        for uri in writer_uris:
            writer = get_attribute(uri, "name")
            writers.append(writer)
        context['writers'] = writers

        # Guests
        guests = []
        guest_uris, guest_role_uris = get_atrributes_bn(eps_uri, "hasGuests", "hasGuest", "playedAs")
        for guest_uri in guest_uris:
            guest_name = get_attribute(guest_uri, "name")
            roles = []
            for role_uri in guest_role_uris[guest_uri]:
                role_name = get_attribute(role_uri, "name")
                roles.append(role_name)
            guests.append({
                "name" : guest_name,
                "roles" : roles
            })
        context['guests'] = guests
        print(1,"k")
        # IMAGE
        image_url = get_attribute(eps_uri, "hasImageEps")
        fandom_url = get_attribute(eps_uri, "hasUrlEps")
        print(5,"k")

        if not fandom_url:
            fandom_url = "https://spongebob.fandom.com/wiki/" + nama_episode.replace(" ", "_")
            response = requests.get(fandom_url)
            print(5.5)
            if "There is currently no text in this page" in response.text:
                fandom_url = None

            if fandom_url:
                image_url = get_image(fandom_url)


        context['fandom'] = fandom_url
        context['image_url'] = image_url
        print("konz")
        # Desc
        print("konz")
        # context['summary'] = get_best_summary(nama_episode)
        # context['synopsis'] = get_synopsis(nama_episode)
        print("konz")
        ############################################################
        return render(request, 'template.html', context)
    else:
        return HttpResponseNotFound(f"Episode '{nama_episode}' tidak ditemukan.")


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
    
def get_imdb_rating(imdb_id):
    try:
        url = f'https://www.imdb.com/title/{imdb_id}/'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            rating_tag = soup.find('span', class_='sc-d541859f-1 imUuxf')
            
            if rating_tag:
                return rating_tag.text
            else:
                return "Rating not found"
        else:
            return f"Error fetching page. Status code: {response.status_code}"
    except:
        return None

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
    return ""

def get_summary_fandom(page_title):
    BASE_URL = "https://spongebob.fandom.com/wiki"
    url = f"{BASE_URL}/{page_title}"
    
    try:
        page_data = fandom.page(page_title)
        summary = page_data.summary
        return summary
    except IndexError:
        print("error, using bs4")
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 13_5_1 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1"
            )
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        tab_line_div = soup.select_one(".mw-parser-output")
        if tab_line_div:
            paragraphs = tab_line_div.find_all("p")
            for p in paragraphs:
                if p.get_text(strip=True):
                    # Remove all <sup> tags
                    for sup in p.find_all("sup"):
                        sup.decompose()
                    summary = p.get_text(strip=False)
                    return summary
    except fandom.error.PageError:
        return ""
    
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

def get_summary_view(request, page_title):
    try:
        summary = get_best_summary(page_title)
        return JsonResponse({'summary': summary})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_synopsis(nama_episode):
    try:
        page = fandom.page(nama_episode)
        data = page.content
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
                if section['title'] in ('Synopsis','Plot'):
                    html_content += dfs(section)  # Mulai DFS untuk bagian Synopsis 
        return html_content
    except:
        return ""

def get_synopsis_view(request, page_title):
    try:
        synopsis = get_synopsis(page_title)
        return JsonResponse({'synopsis': synopsis})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)