"""
Unit tests for HH API client
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
import sys
import os

# Mock config module before importing hh_client
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Create mock config
mock_config = MagicMock()
mock_config.HH_USER_AGENT = 'test-bot/1.0 (test@example.com)'
mock_config.HH_REFRESH_TOKEN = None
mock_config.HH_OAUTH_CLIENT_ID = None
mock_config.HH_OAUTH_CLIENT_SECRET = None
sys.modules['config'] = mock_config

from hh_client import HeadHunterClient


class TestHeadHunterClient(unittest.TestCase):
    """Test HeadHunterClient class"""
    
    def setUp(self):
        """Set up test client"""
        self.client = HeadHunterClient(access_token='test_token', user_agent='test-bot/1.0 (test@example.com)')
    
    def test_client_initialization(self):
        """Test client initialization with token"""
        self.assertEqual(self.client.access_token, 'test_token')
        self.assertIn('Authorization', self.client.session.headers)
        self.assertEqual(
            self.client.session.headers['Authorization'],
            'Bearer test_token'
        )
        # Check User-Agent headers
        self.assertIn('User-Agent', self.client.session.headers)
        self.assertIn('HH-User-Agent', self.client.session.headers)
        self.assertEqual(self.client.session.headers['User-Agent'], 'test-bot/1.0 (test@example.com)')
        self.assertEqual(self.client.session.headers['HH-User-Agent'], 'test-bot/1.0 (test@example.com)')
    
    @patch('hh_client.HeadHunterClient._request_with_retry')
    def test_search_vacancies_success(self, mock_request):
        """Test successful vacancy search"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'X-Request-ID': 'test-123'}
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
        mock_response.headers = {'X-Request-ID': 'test-123'}
        mock_response.json.return_value = {'items': []}
        mock_request.return_value = mock_response
        
        vacancies = self.client.search_vacancies(text='NonExistentJob')
        
        self.assertEqual(len(vacancies), 0)
    
    @patch('hh_client.HeadHunterClient._request_with_retry')
    def test_get_vacancy_details(self, mock_request):
        """Test getting vacancy details"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'X-Request-ID': 'test-123'}
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
    def test_apply_to_vacancy_success_201(self, mock_request):
        """Test successful job application with 201 Created"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {
            'X-Request-ID': 'test-123',
            'Location': 'https://api.hh.ru/negotiations/12345'
        }
        mock_request.return_value = mock_response
        
        result = self.client.apply_to_vacancy(
            vacancy_id='123',
            resume_id='resume_456',
            cover_letter='Test cover letter'
        )
        
        self.assertTrue(result['success'])
        self.assertIn('успешно', result['message'].lower())
        self.assertIn('negotiation_url', result)
        self.assertEqual(result['negotiation_url'], 'https://api.hh.ru/negotiations/12345')
        
        # Verify that data= was used (form-urlencoded)
        call_kwargs = mock_request.call_args[1]
        self.assertIn('data', call_kwargs)
        self.assertNotIn('json', call_kwargs)
    
    @patch('hh_client.HeadHunterClient._request_with_retry')
    def test_apply_to_vacancy_success_200(self, mock_request):
        """Test successful job application with 200 OK"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'X-Request-ID': 'test-123'}
        mock_request.return_value = mock_response
        
        result = self.client.apply_to_vacancy(
            vacancy_id='123',
            resume_id='resume_456',
            cover_letter='Test cover letter'
        )
        
        self.assertTrue(result['success'])
        self.assertIn('успешно', result['message'].lower())
    
    @patch('hh_client.HeadHunterClient._request_with_retry')
    def test_apply_to_vacancy_409_already_applied(self, mock_request):
        """Test application to already applied vacancy (409 Conflict)"""
        mock_response = Mock()
        mock_response.status_code = 409
        mock_response.headers = {'X-Request-ID': 'test-123'}
        mock_request.return_value = mock_response
        
        result = self.client.apply_to_vacancy(
            vacancy_id='123',
            resume_id='resume_456',
            cover_letter='Test cover letter'
        )
        
        # 409 should be treated as success
        self.assertTrue(result['success'])
        self.assertIn('откликались', result['message'].lower())
    
    @patch('hh_client.HeadHunterClient._request_with_retry')
    def test_apply_to_vacancy_400_bad_request(self, mock_request):
        """Test application with 400 bad request"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {'X-Request-ID': 'test-123'}
        mock_response.text = '{"description": "Invalid vacancy_id"}'
        mock_response.json.return_value = {
            'description': 'Invalid vacancy_id',
            'bad_arguments': [{'name': 'vacancy_id', 'description': 'must be set'}]
        }
        mock_request.return_value = mock_response
        
        result = self.client.apply_to_vacancy(
            vacancy_id='123',
            resume_id='resume_456',
            cover_letter='Test cover letter'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('ошибка', result['message'].lower())
    
    @patch('hh_client.HeadHunterClient._request_with_retry')
    def test_apply_to_vacancy_403_forbidden(self, mock_request):
        """Test application with 403 forbidden"""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {'X-Request-ID': 'test-123'}
        mock_response.text = '{"description": "Insufficient permissions"}'
        mock_response.json.return_value = {'description': 'Insufficient permissions'}
        mock_request.return_value = mock_response
        
        result = self.client.apply_to_vacancy(
            vacancy_id='123',
            resume_id='resume_456',
            cover_letter='Test cover letter'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('доступа', result['message'].lower())
    
    @patch('hh_client.HeadHunterClient._request_with_retry')
    def test_apply_to_vacancy_401_with_refresh_success(self, mock_request):
        """Test application with 401 and successful token refresh"""
        # First call returns 401
        mock_response_401 = Mock()
        mock_response_401.status_code = 401
        mock_response_401.headers = {'X-Request-ID': 'test-123'}
        
        # Second call (after refresh) returns 201
        mock_response_201 = Mock()
        mock_response_201.status_code = 201
        mock_response_201.headers = {
            'X-Request-ID': 'test-456',
            'Location': 'https://api.hh.ru/negotiations/12345'
        }
        
        mock_request.side_effect = [mock_response_401, mock_response_201]
        
        with patch.object(self.client, 'refresh_access_token', return_value=True):
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
        mock_response.headers = {'X-Request-ID': 'test-123'}
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
    
    @patch('hh_client.requests.post')
    def test_refresh_access_token_success(self, mock_post):
        """Test successful token refresh"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token'
        }
        mock_post.return_value = mock_response
        
        self.client.refresh_token = 'old_refresh_token'
        
        with patch('hh_client.config') as mock_config:
            mock_config.HH_OAUTH_CLIENT_ID = 'test_client_id'
            mock_config.HH_OAUTH_CLIENT_SECRET = 'test_client_secret'
            
            result = self.client.refresh_access_token()
        
        self.assertTrue(result)
        self.assertEqual(self.client.access_token, 'new_access_token')
        self.assertEqual(self.client.refresh_token, 'new_refresh_token')
        self.assertEqual(
            self.client.session.headers['Authorization'],
            'Bearer new_access_token'
        )
    
    @patch('hh_client.time.sleep')
    def test_retry_with_exponential_backoff(self, mock_sleep):
        """Test retry logic with exponential backoff"""
        with patch.object(self.client, 'session') as mock_session:
            # Mock first two requests to fail with 429, third to succeed
            mock_response_fail = Mock()
            mock_response_fail.status_code = 429
            mock_response_fail.headers = {'Retry-After': '2', 'X-Request-ID': 'test-123'}
            
            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.headers = {'X-Request-ID': 'test-456'}
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
