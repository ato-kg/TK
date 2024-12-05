from SPARQLWrapper import JSON, SPARQLWrapper


class RDFManager:
    _instance = None

    def __new__(cls, sparql_endpoint=None):
        if cls._instance is None:
            if sparql_endpoint is None:
                raise ValueError("SPARQL endpoint must be provided for the first initialization.")
            cls._instance = super(RDFManager, cls).__new__(cls)
            cls._instance.sparql_endpoint = sparql_endpoint
            cls._instance.sparql = SPARQLWrapper(sparql_endpoint)
        return cls._instance

    def query(self, sparql_query, params=None):
        """
        Execute a SPARQL query with optional parameters to prevent injection.
        
        :param sparql_query: SPARQL query string
        :param params: Dictionary of query parameters to replace
        """
        # Replace placeholders with sanitized values
        if params:
            for key, value in params.items():
                # Sanitize value

                sparql_query = sparql_query.replace(f"?{key}", f"'{value.replace("'","\\'").replace('"','\\"')}'")
        
        # Configure SPARQLWrapper
        # print(sparql_query)
        self.sparql.setQuery(sparql_query)
        self.sparql.setReturnFormat(JSON)
        # print(sparql_query)
        response = self.sparql.query()
        
        # Return JSON results
        return response.convert()["results"]["bindings"]
