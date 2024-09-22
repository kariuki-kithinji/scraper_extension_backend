from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin
import phonenumbers


class Scraper:
    social_media_domains = {
        'facebook': r'facebook\.com/(?!share|sharer|login|signup|groups)[\w.-]+/?$',
        'twitter': r'twitter\.com/(?!share|intent|home|search)[\w.-]+/?$',
        'linkedin': r'linkedin\.com/(?:company/|in/|profile/view\?id=)[\w.-]+/?$',
        'instagram': r'instagram\.com/[\w.-]+/?$',
        'youtube': r'youtube\.com/(?:channel/|user/|c/)[\w.-]+/?$',
        'tiktok': r'tiktok\.com/@[\w.-]+/?$',
        'pinterest': r'pinterest\.com/[\w.-]+/?$',
        'github': r'github\.com/[\w.-]+/?$',
        'medium': r'medium\.com/@[\w.-]+/?$',
        'reddit': r'reddit\.com/user/[\w.-]+/?$',
        'tumblr': r'[\w.-]+\.tumblr\.com/?$',
        'snapchat': r'snapchat\.com/add/[\w.-]+/?$',
        'vimeo': r'vimeo\.com/(?:channels/|groups/|albums/|)[\w.-]+/?$',
        'soundcloud': r'soundcloud\.com/[\w.-]+/?$',
        'behance': r'behance\.net/[\w.-]+/?$',
        'dribbble': r'dribbble\.com/[\w.-]+/?$',
        'quora': r'quora\.com/profile/[\w.-]+/?$',
        'flickr': r'flickr\.com/people/[\w@.-]+/?$',
        'deviantart': r'deviantart\.com/[\w.-]+/?$',
        'wordpress': r'[\w.-]+\.wordpress\.com/?$',
    }

    def __init__(self, html_content, base_url=None):
        self.soup = BeautifulSoup(html_content, 'lxml')
        self.base_url = base_url
        self.blacklist = set()

    def set_blacklist(self, blacklist):
        """Set a blacklist of domains or patterns to ignore."""
        self.blacklist = set(blacklist)

    def is_blacklisted(self, url):
        """Check if a URL is blacklisted."""
        parsed_url = urlparse(url)
        return any(re.search(pattern, parsed_url.netloc) for pattern in self.blacklist)


    def extract_social_links(self):
        links = self.soup.find_all('a', href=True)
        social_links = {}
        for link in links:
            href = link['href'].lower()
            if self.base_url:
                href = urljoin(self.base_url, href)
            if self.is_blacklisted(href):
                continue
            for platform, pattern in self.social_media_domains.items():
                if re.search(pattern, href):
                    if platform not in social_links:
                        social_links[platform] = set()
                    social_links[platform].add(href)
        return {k: list(v) for k, v in social_links.items()}

    def extract_emails(self):
        # Email pattern to match standard emails in the text
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        
        # Find all emails in the plain text
        emails_in_text = set(re.findall(email_pattern, self.soup.get_text()))
        
        # Find all mailto: links in the HTML content
        mailto_links = self.soup.select('a[href^=mailto]')
        
        emails_in_mailto = set()
        for link in mailto_links:
            href = link.get('href', '')
            if href.startswith('mailto:'):
                # Remove the 'mailto:' part and strip any parameters like ?subject=...
                parsed_email = href[7:].split('?')[0]
                if self.is_valid_email(parsed_email):
                    emails_in_mailto.add(parsed_email)
        
        # Combine both sets of emails
        all_emails = emails_in_text.union(emails_in_mailto)
        
        # Filter out blacklisted emails, ensuring robustness with proper mailto handling
        return [email for email in all_emails if not self.is_blacklisted(f"mailto:{email}")]

    def is_valid_email(self, email):
        """Performs additional validation on extracted email addresses to filter out malformed ones."""
        # Basic email validation to ensure the format is correct
        email_pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}$'
        return re.match(email_pattern, email) is not None

    def extract_phone_numbers(self):
        phone_patterns = [
            # US/Canada
            r'\b(?:\+1\s*[\-\.\(\)]*)?(?:\(?([2-9][0-9]{2})\)?[\-\.\s]*)?([2-9][0-9]{2})[\-\.\s]*([0-9]{4})\b',
            # UK
            r'\b(?:\+44\s?|\(?0\)?)([1-9][0-9]{1,4})\s?([0-9]{4,6})\b',
            # Germany
            r'\b(?:\+49\s?|\(?0\)?)([1-9][0-9]{1,4})\s?([0-9]{4,7})\b',
            # France
            r'\b(?:\+33\s?|\(?0\)?)([1-9][0-9]{1,9})\b',
            # Japan
            r'\b(?:\+81\s?|\(?0\)?)([0-9]{2,4})[\-\.\s]?([0-9]{2,4})[\-\.\s]?([0-9]{4})\b',
            # General international phone numbers
            r'\b(?:\+\d{1,3}\s*[-.\(\)]*)?(?:\(?\d{1,4}\)?[-.\s]*)?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b'
        ]

        phone_numbers = set()
        text = self.soup.get_text()
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Reconstruct the phone number from the match groups
                if isinstance(match, tuple):
                    match = ''.join(match)
                # Clean up extra spaces or separators
                clean_number = re.sub(r'[^\d\+]', '', match)
                phone_numbers.add(clean_number)
        
        validated_numbers = []
        for number in phone_numbers:
            try:
                parsed_number = phonenumbers.parse(number)
                if phonenumbers.is_valid_number(parsed_number):
                    validated_numbers.append(phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164))
            except phonenumbers.NumberParseException:
                continue
        
        return validated_numbers

    def extract_addresses(self):
        # Refined patterns for different address formats
        address_patterns = [
            # US Address: Street number, street name, city, state abbreviation, zip code
            r'\d{1,5}\s+(?:[A-Za-z0-9.-]+\s+){1,3}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Place|Pl|Court|Ct)\.?(?:\s+(?:Apt|Suite|Unit)\s+\d+)?(?:,?\s+[A-Za-z\s]+,?\s+[A-Z]{2}\s+\d{5}(?:-\d{4})?)',
            
            # UK Address: Street number, street name, optionally city, UK postal code
            r'\d{1,4}\s+[A-Za-z\s]+(?:,\s*[A-Za-z\s]+)*,\s*[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}',
            
            # General International Address: Street number, street name, postal code
            r'\d{1,5}(?:[\w\s,-]+)?(?:street|avenue|road|boulevard|lane|drive|way|place|court)[\w\s,-]+\d{4,6}'
        ]
        
        # Set to store unique addresses
        addresses = set()
        
        # Apply patterns and collect matches
        for pattern in address_patterns:
            matches = re.findall(pattern, self.soup.get_text(), re.IGNORECASE)
            for match in matches:
                if self.is_valid_address(match):
                    addresses.add(match.strip())
        
        return list(addresses)

    def is_valid_address(self, address):
        """
        Basic address validation to reduce false positives.
        You can add more complex validation rules here based on your data.
        """
        # Check if the address contains some form of a street type (e.g., 'St', 'Ave', 'Rd')
        street_keywords = ['street', 'st', 'avenue', 'ave', 'road', 'rd', 'boulevard', 'blvd', 'lane', 'ln', 'drive', 'dr', 'way', 'place', 'court', 'ct']
        
        # Ensure the address contains a keyword and numbers (like house numbers, zip codes)
        if any(keyword in address.lower() for keyword in street_keywords) and re.search(r'\d', address):
            return True
        return False

    def extract_rss_feeds(self):
        """Extract RSS feed links from the HTML content."""
        rss_links = set()
        
        # Look for link tags with type "application/rss+xml" or "application/atom+xml"
        for link in self.soup.find_all('link', type=re.compile(r'(rss|atom)\+xml')):
            href = link.get('href')
            if href:
                if self.base_url:
                    href = urljoin(self.base_url, href)
                if not self.is_blacklisted(href):
                    rss_links.add(href)
        
        # Look for 'a' tags with href containing 'rss' or 'feed'
        for link in self.soup.find_all('a', href=re.compile(r'(rss|feed)', re.I)):
            href = link.get('href')
            if href:
                if self.base_url:
                    href = urljoin(self.base_url, href)
                if not self.is_blacklisted(href):
                    rss_links.add(href)
        
        return list(rss_links)

    def extract_all(self):
        return {
            'social_links': self.extract_social_links(),
            'emails': self.extract_emails(),
            'phone_numbers': self.extract_phone_numbers(),
            'addresses': self.extract_addresses(),
            'rss_feeds': self.extract_rss_feeds(),
        }

def flatten_data(input_data):
    # Create a new dictionary to store the flattened data
    flattened = {}

    # Flatten social links (Twitter, LinkedIn, etc.)
    social_links = input_data.get('social_links', {})
    if isinstance(social_links, dict):
        for platform, links in social_links.items():
            flattened[platform] = '??'.join(links) if isinstance(links, list) else str(links)

    # Flatten emails, phone numbers, and addresses
    flattened['emails'] = '??'.join(input_data.get('emails', []))
    flattened['phone_numbers'] = '??'.join(input_data.get('phone_numbers', []))
    flattened['addresses'] = '??'.join(input_data.get('addresses', []))

    # Flatten RSS feeds
    flattened['rss_feeds'] = '??'.join(input_data.get('rss_feeds', []))

    # Handle any unlisted categories dynamically
    for key, value in input_data.items():
        # Skip the keys that have already been handled
        if key in ['social_links', 'emails', 'phone_numbers', 'addresses', 'rss_feeds']:
            continue

        # If the value is a list, flatten it
        if isinstance(value, list):
            flattened[key] = '??'.join(map(str, value))
        
        # If the value is a dictionary, flatten it by key and subkey
        elif isinstance(value, dict):
            for subkey, subvalue in value.items():
                if isinstance(subvalue, list):
                    flattened[f'{subkey}'] = '??'.join(map(str, subvalue))
                else:
                    flattened[f'{subkey}'] = str(subvalue)
        
        # If the value is neither a list nor a dictionary (e.g., a string or number)
        else:
            flattened[key] = str(value)

    return flattened


# Example usage:
if __name__ == "__main__":
    html_content = '''
    <html>
        <head>
            <link rel="alternate" type="application/rss+xml" title="RSS Feed" href="/rss.xml">
        </head>
        <body>
            <a href="https://www.facebook.com/userprofile">Facebook</a>
            <a href="https://www.twitter.com/user">Twitter</a>
            <a href="https://www.linkedin.com/in/johnsmith">LinkedIn</a>
            <a href="mailto:someone@example.com">Email Us</a>
            <p>Contact us at +1 (800) 555-1234 or +44 20 7123 4567</p>
            <p>Our US office is at 1234 Elm Street, Springfield, IL 62701</p>
            <p>Our UK office is at 10 Downing Street, London, SW1A 2AA</p>
            <a href="/feed">RSS Feed</a>
        </body>
    </html>
    '''
    extractor = Scraper(html_content, base_url="https://www.example.com")
    extractor.set_blacklist(['facebook.com'])  # Example: blacklist Facebook
    contact_info = extractor.extract_all()
    print(contact_info)