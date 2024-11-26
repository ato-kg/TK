from django.apps import AppConfig

from rdfapp.rdf_manager import RDFManager
from rdfapp.wikidata_manager import WikidataManager


class RdfappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rdfapp'
    def ready(self):
        global rdf_manager, wikidata_manager
        rdf_manager = RDFManager("http://localhost:7200/repositories/TK")
        wikidata_manager = WikidataManager()
