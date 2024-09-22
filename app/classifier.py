import os
import pickle
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report

class WebsiteClassifier:
    def __init__(self, model_path='website_classifier_model.pkl'):
        self.model_path = model_path
        self.pipeline = None

    def load_data(self, csv_file):
        """Loads CSV data and splits it into training and testing sets."""
        data = pd.read_csv(csv_file)
        X = data['cleaned_website_text']
        y = data['Category']
        return train_test_split(X, y, test_size=0.2, random_state=42)

    def build_pipeline(self):
        """Builds the text classification pipeline."""
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(stop_words='english', max_df=0.9)),
            ('clf', LogisticRegression())
        ])

    def train_model(self, X_train, y_train):
        """Trains the model."""
        self.build_pipeline()  # Ensure the pipeline is built before training
        self.pipeline.fit(X_train, y_train)
        self.save_model()

    def save_model(self):
        """Saves the trained model to a file."""
        with open(self.model_path, 'wb') as model_file:
            pickle.dump(self.pipeline, model_file)

    def load_model(self):
        """Loads the model from a file, if it exists."""
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as model_file:
                self.pipeline = pickle.load(model_file)
            print(f"Model loaded from {self.model_path}")
        else:
            print(f"Model not found at {self.model_path}, retraining...")
            self.pipeline = None  # Ensures pipeline is None so retraining happens

    def ensure_model_is_trained(self, X_train, y_train):
        """Ensures the model is trained, either by loading or retraining."""
        self.load_model()
        if self.pipeline is None:
            self.train_model(X_train, y_train)

    def evaluate_model(self, X_test, y_test):
        """Evaluates the model on the test set."""
        if self.pipeline is None:
            print("Model not trained.")
            return
        y_pred = self.pipeline.predict(X_test)
        print(f"Accuracy: {accuracy_score(y_test, y_pred)}")
        print(f"Classification Report:\n{classification_report(y_test, y_pred, zero_division=0)}")

    def classify_website(self, cleaned_text):
        """Classifies a new website based on cleaned text."""
        if self.pipeline is None:
            raise ValueError("Model is not loaded or trained. Please ensure the model is trained.")
        return self.pipeline.predict([cleaned_text])[0]


    
# Example usage:
if __name__ == "__main__":
    classifier = WebsiteClassifier()

    # Load data and split into train/test sets
    X_train, X_test, y_train, y_test = classifier.load_data('website_classification.csv')

    # Ensure the model is trained (load or retrain if necessary)
    classifier.ensure_model_is_trained(X_train, y_train)

    # Evaluate the model
    classifier.evaluate_model(X_test, y_test)

    # Classify new websites
    test_website_texts = [
        "Find the best hotel deals with Expedia. Book flights, hotels, vacation packages, and car rentals for your next holiday. Trusted by millions of travelers for affordable travel solutions.",
        "Shop for the latest fashion trends at unbeatable prices on Amazon. Discover a wide range of clothing, accessories, and electronics. Fast delivery and excellent customer service guaranteed.",
        "Stay updated with the latest world news, politics, sports, and entertainment on CNN. Breaking news, analysis, and expert opinions all in one place.",
        "Access free online courses and educational resources on Coursera. Learn new skills from top universities and companies in various fields such as data science, business, and computer science.",
        "Connect with friends and family on Facebook. Share photos, updates, and experiences."
    ]

    for text in test_website_texts:
        predicted_category = classifier.classify_website(text)
        print(f"Predicted Category: {predicted_category}")
