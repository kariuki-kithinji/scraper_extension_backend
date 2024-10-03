import json
import whois
import wikipedia
from urllib.parse import urlparse
import socket
import requests
import spacy

class DomainInfo:
    def __init__(self, url):
        self.url = url
        self.domain_name = self.extract_domain_name()
        self._nlp = None  # spaCy model will be loaded lazily
        self._wikipedia_summary = None
        self._whois_info = None
        self._ip_address = None
        self._server_location = None
        self._location_info = None
        self.country_code = self.get_country_code()

    def extract_domain_name(self):
        parsed_url = urlparse(self.url)
        domain = parsed_url.netloc.replace('www.', '')  # Remove 'www.' if present
        parts = domain.split('.')
        return parts[0] if len(parts) > 1 else domain  # Return the main domain part

    def load_spacy_model(self):
        if self._nlp is None:
            self._nlp = spacy.load("en_core_web_sm")
        return self._nlp

    def get_wikipedia_summary(self):
        if self._wikipedia_summary is not None:
            return self._wikipedia_summary

        try:
            search_results = wikipedia.search(self.domain_name)
            if search_results:
                page_title = search_results[0]  # Take the most relevant result
                page = wikipedia.page(page_title)
                page_id = page.pageid
                full_page = wikipedia.WikipediaPage(pageid=page_id)
                self._wikipedia_summary = full_page.content
            else:
                self._wikipedia_summary = 'No Wikipedia page found.'
        except wikipedia.exceptions.DisambiguationError as e:
            self._wikipedia_summary = f"Disambiguation Error: {e.options}"
        except wikipedia.exceptions.PageError:
            self._wikipedia_summary = 'No Wikipedia page found.'
        
        return self._wikipedia_summary

    def extract_location(self):
        if self._location_info is not None:
            return self._location_info

        summary = self.get_wikipedia_summary()
        nlp = self.load_spacy_model()
        doc = nlp(summary)

        # Extract location names using list comprehension
        self._location_info = list(set(ent.text for ent in doc.ents if ent.label_ in ["GPE", "LOC"]))
        return self._location_info

    def get_location_data(self):
        return self.extract_location()

    def get_ip_address(self):
        if self._ip_address is not None:
            return self._ip_address

        try:
            parsed_url = urlparse(self.url)
            hostname = parsed_url.netloc.replace('www.', '')
            self._ip_address = socket.gethostbyname(hostname)
        except socket.error as e:
            self._ip_address = f"Error retrieving IP address: {str(e)}"

        return self._ip_address

    def get_server_location(self):
        if self._server_location is not None:
            return self._server_location

        ip_address = self.get_ip_address()
        if not ip_address or "Error" in ip_address:
            self._server_location = "Unable to retrieve server location."
            return self._server_location

        # Use a public IP geolocation API
        try:
            response = requests.get(f"https://ipinfo.io/{ip_address}/json")
            data = response.json()
            self._server_location = {
                'IP Address': ip_address,
                'City': data.get('city', 'N/A'),
                'Region': data.get('region', 'N/A'),
                'Country': data.get('country', 'N/A'),
                'Location': data.get('loc', 'N/A')  # Lat, Long
            }
        except requests.RequestException as e:
            self._server_location = f"Error retrieving server location: {str(e)}"

        return self._server_location

    def get_country_code(self):
        domain_parts = self.url.split('.')
        if len(domain_parts) > 1:
            tld = domain_parts[-1].upper()
            # Check if the TLD is a country code
            if len(tld) == 2 and tld.isalpha():
                return tld
        return 'N/A'

    def get_whois_info(self):
        if self._whois_info is not None:
            return self._whois_info

        try:
            domain_info = whois.whois(self.url)
            self._whois_info = {
                'Domain Name': domain_info.domain_name,
                'Registrar': domain_info.registrar,
                #'Creation Date': str(domain_info.creation_date),
                #'Expiration Date': str(domain_info.expiration_date),
                'Registrant Name': domain_info.registrant_name,
                'Registrant Organization': domain_info.registrant_organization,
                'Registrant Country': domain_info.registrant_country
            }
        except Exception as e:
            self._whois_info = f"Error retrieving WHOIS information: {str(e)}"

        return self._whois_info

def get_all_domain_info(url):
    domain_info = DomainInfo(url)

    # Collect all the relevant information
    data = {
        'Domain Name': domain_info.domain_name,
        'WHOIS Info': domain_info.get_whois_info(),
        'IP Address': domain_info.get_ip_address(),
        'Server Location': domain_info.get_server_location(),
        #'Extracted Locations': domain_info.get_location_data(),
        'Country Code': domain_info.get_country_code()
    }

    # Convert to JSON format
    return data 

# Example usage:
if __name__ == "__main__":
    url = 'https://example.com'
    domain_info = DomainInfo(url)
    print("Domain Name:", domain_info.domain_name)
    print("Extracted Location Data:", domain_info.get_location_data())
    print("WHOIS Information:", domain_info.get_whois_info())
    print("Server Location:", domain_info.get_server_location())
    print("Country Code from Domain:", domain_info.country_code)
