import logging
import re
import time
from functools import lru_cache

from SPARQLWrapper import JSON, SPARQLWrapper


class WikidataManager:
    _instance = None

    def __new__(cls, sparql_endpoint="https://query.wikidata.org/sparql"):
        """
        Singleton pattern: Ensures only one instance of WikidataManager is created.
        """
        if cls._instance is None:
            cls._instance = super(WikidataManager, cls).__new__(cls)
            cls._instance.sparql_endpoint = sparql_endpoint
            cls._instance.sparql = SPARQLWrapper(sparql_endpoint)
        return cls._instance

    def query(self, sparql_query, retries=3):
        """
        Execute a SPARQL query with retry logic for rate limiting and logging.

        :param sparql_query: SPARQL query string
        :param retries: Number of retries in case of rate limiting
        :return: JSON results from Wikidata
        """
        self.sparql.setQuery(sparql_query)
        self.sparql.setReturnFormat(JSON)
        for attempt in range(retries):
            try:
                response = self.sparql.query()
                if response.response.status == 429:  # Rate limit exceeded
                    if attempt < retries - 1:
                        logging.warning("Rate limit exceeded. Retrying...")
                        time.sleep(5)  # Wait before retrying
                        continue
                    else:
                        raise Exception("Rate limit exceeded. Try again later.")
                if response.response.status >= 400:
                    raise Exception(f"HTTP Error {response.response.status}: {response.response.reason}")
                return response.convert()["results"]["bindings"]
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(5)
                else:
                    logging.error(f"SPARQL query failed: {e}")
                    raise

    @lru_cache(maxsize=100)
    def get_specific_attributes(self, entity_uri, attributes):
        """
        Fetch specific attributes from a Wikidata entity.

        :param entity_uri: Full URI of the Wikidata entity (e.g., "http://www.wikidata.org/entity/Q20439681")
        :param attributes: List of property IDs to fetch (e.g., ["P31", "P1476"])
        :return: Dictionary of requested attributes
        """
        if not attributes:
            raise ValueError("Attributes list cannot be empty.")

        entity_id = entity_uri.split("/")[-1]  # Extract QID (e.g., "Q20439681")
        attribute_select = " ".join([f"wdt:{attr} ?{attr}" for attr in attributes])
        sparql_query = f"""
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>

        SELECT { " ".join([f"?{attr}" for attr in attributes]) }
        WHERE {{
            wd:{entity_id} {attribute_select} .
        }}
        """
        results = self.query(sparql_query)

        # Parse results into a dictionary
        if results:
            return {attr: results[0].get(attr, {}).get("value", None) for attr in attributes}
        return {attr: None for attr in attributes}  # Return None for missing attributes

    @lru_cache(maxsize=100)
    def get_attribute(self, uri_subject, uri_property):
        """
        Get the object URI for a given subject and property in Wikidata.

        :param uri_subject: Full URI of the Wikidata entity (e.g., "http://www.wikidata.org/entity/Q20439681")
        :param uri_property: Full URI of the Wikidata property (e.g., "http://www.wikidata.org/prop/direct/P31")
        :return: URI of the object (if found), or None
        """
        
        subject_id = uri_subject.split("/")[-1]  # Extract QID from URI
        property_id = uri_property.split("/")[-1]  # Extract PID from URI

        # SPARQL query to fetch the object URI for the given subject and property
        sparql_query = f"""
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>

        SELECT ?object
        WHERE {{
            wd:{subject_id} wdt:{property_id} ?object .
        }}
        """
        return self.query(sparql_query)
