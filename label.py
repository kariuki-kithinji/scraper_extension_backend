import csv
import json
import cohere
from tqdm import tqdm
import pickle
import os
import time

# Initialize Cohere client
api_key = "WQO3QwvZesAYw9gSdLlJdObvPaMQoLgbIR1bgEZg"
co = cohere.Client(api_key=api_key, log_warning_experimental_features=False)

# Cache file path
cache_file = 'cache.pkl'

# Function to load cache from a file
def load_cache():
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    return {}

# Function to save cache to a file in batches
def save_cache_batch(cache, save_interval=100):
    # Write the cache to disk every `save_interval` number of calls
    if len(cache) % save_interval == 0:
        with open(cache_file, 'wb') as f:
            pickle.dump(cache, f)

# Load cache at the start
cache = load_cache()

# Function to categorize text using Cohere's chat model
def categorize_text(text, categories):
    # Check if the result is cached
    if text in cache:
        return cache[text] , True
    
    # Send the request to Cohere if not cached
    try:
        response = co.chat(
            model="command-r-plus",
            message=f"Categorize the following text into one of the given categories. You must choose a category and return only the string of the selected category : categories = {categories}.\nText= {text}",
        )
        category = response.text
    except Exception as e:
        category = "Other: API request failed"
    
    # Cache the result
    cache[text] = category
    save_cache_batch(cache)
    
    return category , False

# Function to read CSV, categorize and output results with progress bar and rate limiting
def process_csv(file_path, categories, output_file):
    calls_made = 0  # Track the number of API calls made
    start_time = time.time()  # Track the start time for rate-limiting

    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        # Assuming the first row is the header
        headers = next(reader)
        text_column_index = headers.index("cleaned_website_text")  # Assuming the column is named "cleaned_website_text"
        
        rows = list(reader)
        results = []

        # Initialize tqdm for progress
        with tqdm(total=len(rows), desc="Processing Text") as pbar:
            for row in rows:
                text = row[text_column_index]
                category , from_cache = categorize_text(text, categories) ## category is a json object in this format {category:chosen category} , parse it correctly
                
                row.append(category)
                results.append(row)
                pbar.update(1)
                
                if not from_cache:
                    # Rate limiting logic
                    calls_made += 1
                    if calls_made >= 40:
                        elapsed_time = time.time() - start_time
                        if elapsed_time < 60:
                            time.sleep(60 - elapsed_time)  # Sleep for the remaining time in the minute
                        # Reset the count and start time
                        calls_made = 0
                        start_time = time.time()
    
    # Write results to output CSV
    with open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(headers + ["relabelled_category"])  # Add new "category" column
        writer.writerows(results)

# List of categories provided by the user
categories = [
    "Media", "Transport", "Government", "Utility", "Fire", "Police", "School",
    "Other: Computers and Technology", "Other: Streaming Services", "Other: Sports",
    "Other: Games", "Other: E-Commerce", "Weather", "Other: Food",
    "Other: Photography", "Other: Health and Fitness", "Other: Social Networking & Messaging",
    "Other: Forums"
]

# Example of usage:
csv_file_path = "website_classification.csv"  # Update with your actual CSV file path
output_file = "classified_results.csv"  # Path for saving the categorized results

# Process the CSV file and categorize the text with caching, progress bar, and rate-limiting
process_csv(csv_file_path, categories, output_file)

