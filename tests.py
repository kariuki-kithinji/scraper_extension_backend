import unittest
import requests
import json
from unittest.mock import patch, MagicMock

class APITestCase(unittest.TestCase):
    BASE_URL = 'http://localhost:5000/api/v1'  # Adjust this to your API's base URL

    def test_analyze_social(self):
        url = f"{self.BASE_URL}/analysis/social"
        data = {'html': 'test_html', 'url': 'http://test.com'}
        response = requests.post(url, json=data)
        self.assertEqual(response.status_code, 202)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'success')
        self.assertIn('task_id', response_data)

    def test_analyze_classification(self):
        url = f"{self.BASE_URL}/analysis/classification"
        data = {'html': 'test_html'}
        response = requests.post(url, json=data)
        self.assertEqual(response.status_code, 202)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'success')
        self.assertIn('task_id', response_data)

    def test_analyze_location(self):
        url = f"{self.BASE_URL}/analysis/location"
        data = {'url': 'http://test.com'}
        response = requests.post(url, json=data)
        self.assertEqual(response.status_code, 202)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'success')
        self.assertIn('task_id', response_data)

    def test_get_task_status(self):
        task_id = 'test_task_id'  # You might want to create a real task first
        url = f"{self.BASE_URL}/tasks/{task_id}"
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn('task_id', response_data)
        self.assertIn('state', response_data)

    def test_flag_record(self):
        record_id = 1  # You might want to create a real record first
        url = f"{self.BASE_URL}/records/{record_id}/flag"
        response = requests.post(url)
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'success')
        self.assertEqual(response_data['message'], 'Record flagged successfully')

    def test_save_record(self):
        record_id = 1  # You might want to create a real record first
        url = f"{self.BASE_URL}/records/{record_id}/save"
        response = requests.post(url)
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'success')
        self.assertEqual(response_data['message'], 'Record saved successfully')

    def test_get_record(self):
        record_id = 1  # You might want to create a real record first
        url = f"{self.BASE_URL}/records/{record_id}"
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn('url', response_data)
        self.assertIn('html_hash', response_data)

    def test_get_all_records(self):
        url = f"{self.BASE_URL}/records"
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIsInstance(response_data, list)
        if response_data:  # If there are any records
            self.assertIn('url', response_data[0])
            self.assertIn('html_hash', response_data[0])

if __name__ == '__main__':
    unittest.main()