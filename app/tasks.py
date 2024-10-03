from celery import Celery
from bs4 import BeautifulSoup
from app.scrape import Scraper
from app.classifier import WebsiteClassifier
from app.domain import get_all_domain_info
from celery.signals import task_success

celery = Celery()

classifier = WebsiteClassifier()
X_train, X_test, y_train, y_test = classifier.load_data('website_classification.csv')
classifier.ensure_model_is_trained(X_train, y_train)
classifier.evaluate_model(X_test, y_test)


@celery.task(bind=True, rate_limit='100/s')
def social_queue_manager(self, html, url):
    try:
        print(f"Starting social_queue_manager task for URL: {url}")
        extractor = Scraper(html, url)
        parsed_data = extractor.extract_all()
        print(f"Finished social_queue_manager task for URL: {url}")
        return parsed_data
    except Exception as e:
        print(f"Error in social_queue_manager: {str(e)}")
        return None

@celery.task(bind=True, rate_limit='100/s')
def classifier_queue_manager(self, html):
    try:
        print("Starting classifier_queue_manager task")
        soup = BeautifulSoup(html, 'lxml')
        predicted_category = classifier.classify_website(soup.get_text())
        print(f"Classification result: {predicted_category}")
        return {"predicted":predicted_category}
    except Exception as e:
        print(f"Error in classifier_queue_manager: {str(e)}")
        return None

@celery.task(bind=True, rate_limit='50/s')
def location_queue_manager(self, url):
    try:
        print(f"Starting location_queue_manager task for URL: {url}")
        data = get_all_domain_info(url)
        print(f"Location data for URL: {url}: {data}")
        return data
    except Exception as e:
        print(f"Error in location_queue_manager: {str(e)}")
        return None

