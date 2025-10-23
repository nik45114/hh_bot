"""
Unit tests for HH API client
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
from hh_client import HeadHunterClient


class TestHeadHunterClient(unittest.TestCase):
    """Test HeadHunterClient class"""
    
    def setUp(self):
        """Set up test client"""
        self.client = HeadHunterClient(access_token='test_token')
    
    def test_client_initialization(self):
        """Test client initialization with token"""
        self.assertEqual(self.client.access_token, 'test_token')
        self.assertIn('Authorization', self.client.session.headers)
        self.assertEqual(
            self.client.session.headers['Authorization'],
            'Bearer test_token'
        )
    
    @patch('hh_client.HeadHunterClient._request_with_retry')
    def test_search_vacancies_success(self, mock_request):
        """Test successful vacancy search"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [
                {'id': '123', 'name': 'Python Developer'},
                {'id': '456', 'name': 'Backend Developer'}
            ]
        }
        mock_request.return_value = mock_response
        
        # Test search
        vacancies = self.client.search_vacancies(text='Python')
        
        self.assertEqual(len(vacancies), 2)
        self.assertEqual(vacancies[0]['id'], '123')
        self.assertEqual(vacancies[1]['id'], '456')
    
    @patch('hh_client.HeadHunterClient._request_with_retry')
    def test_search_vacancies_empty_result(self, mock_request):
        """Test vacancy search with no results"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'items': []}
        mock_request.return_value = mock_response
        
        vacancies = self.client.search_vacancies(text='NonExistentJob')
        
        self.assertEqual(len(vacancies), 0)
    
    @patch('hh_client.HeadHunterClient._request_with_retry')
    def test_get_vacancy_details(self, mock_request):
        """Test getting vacancy details"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': '123',
            'name': 'Python Developer',
            'description': 'Test description'
        }
        mock_request.return_value = mock_response
        
        details = self.client.get_vacancy_details('123')
        
        self.assertIsNotNone(details)
        self.assertEqual(details['id'], '123')
        self.assertEqual(details['name'], 'Python Developer')
    
    @patch('hh_client.HeadHunterClient._request_with_retry')
    def test_apply_to_vacancy_success(self, mock_request):
        """Test successful job application"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_request.return_value = mock_response
        
        result = self.client.apply_to_vacancy(
            vacancy_id='123',
            resume_id='resume_456',
            cover_letter='Test cover letter'
        )
        
        self.assertTrue(result['success'])
        self.assertIn('успешно', result['message'].lower())
    
    @patch('hh_client.HeadHunterClient._request_with_retry')
    def test_apply_to_vacancy_rate_limit(self, mock_request):
        """Test application with rate limiting"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_request.return_value = mock_response
        
        result = self.client.apply_to_vacancy(
            vacancy_id='123',
            resume_id='resume_456',
            cover_letter='Test cover letter'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('лимит', result['message'].lower())
    
    def test_apply_without_token(self):
        """Test application without access token"""
        client = HeadHunterClient()  # No token
        
        result = client.apply_to_vacancy(
            vacancy_id='123',
            resume_id='resume_456',
            cover_letter='Test cover letter'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('токен', result['message'].lower())
    
    @patch('hh_client.time.sleep')
    def test_retry_with_exponential_backoff(self, mock_sleep):
        """Test retry logic with exponential backoff"""
        with patch.object(self.client, 'session') as mock_session:
            # Mock first two requests to fail with 429, third to succeed
            mock_response_fail = Mock()
            mock_response_fail.status_code = 429
            mock_response_fail.headers = {'Retry-After': '2'}
            
            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {'items': []}
            
            mock_session.request.side_effect = [
                mock_response_fail,
                mock_response_fail,
                mock_response_success
            ]
            
            response = self.client._request_with_retry('GET', 'http://test.com')
            
            # Should have made 3 attempts
            self.assertEqual(mock_session.request.call_count, 3)
            # Should have slept twice
            self.assertEqual(mock_sleep.call_count, 2)
            # Final response should be successful
            self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
