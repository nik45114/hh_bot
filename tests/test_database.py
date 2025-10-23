"""
Unit tests for database operations
"""
import unittest
import tempfile
import os
from datetime import datetime
from storage.database import Database


class TestDatabase(unittest.TestCase):
    """Test Database class"""
    
    def setUp(self):
        """Create temporary database for testing"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = Database(self.temp_db.name)
    
    def tearDown(self):
        """Clean up temporary database"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_create_user(self):
        """Test user creation"""
        user = self.db.get_or_create_user(12345, 'testuser')
        self.assertIsNotNone(user)
        self.assertEqual(user['chat_id'], 12345)
        self.assertEqual(user['username'], 'testuser')
    
    def test_get_preferences(self):
        """Test getting user preferences"""
        self.db.get_or_create_user(12345, 'testuser')
        prefs = self.db.get_preferences(12345)
        
        self.assertIsNotNone(prefs)
        self.assertEqual(prefs['role_domain'], 'IT')
        self.assertEqual(prefs['remote_only'], False)
        self.assertEqual(prefs['keywords'], [])
    
    def test_update_preferences(self):
        """Test updating user preferences"""
        self.db.get_or_create_user(12345, 'testuser')
        
        # Update preferences
        self.db.update_preferences(
            12345,
            role_domain='Management',
            remote_only=True,
            keywords=['Python', 'Django'],
            roles=['Team Lead', 'Project Manager']
        )
        
        # Verify updates
        prefs = self.db.get_preferences(12345)
        self.assertEqual(prefs['role_domain'], 'Management')
        self.assertEqual(prefs['remote_only'], True)
        self.assertEqual(prefs['keywords'], ['Python', 'Django'])
        self.assertEqual(prefs['roles'], ['Team Lead', 'Project Manager'])
    
    def test_roles_serialization(self):
        """Test that roles are properly serialized/deserialized"""
        self.db.get_or_create_user(12345, 'testuser')
        
        # Set multiple roles
        test_roles = ['Руководитель', 'Project Manager', 'Team Lead']
        self.db.update_preferences(12345, roles=test_roles)
        
        # Retrieve and verify
        prefs = self.db.get_preferences(12345)
        self.assertEqual(prefs['roles'], test_roles)
        self.assertIsInstance(prefs['roles'], list)
        self.assertEqual(len(prefs['roles']), 3)
    
    def test_vacancy_deduplication(self):
        """Test vacancy sent/processed tracking"""
        self.db.get_or_create_user(12345, 'testuser')
        
        # Test sent vacancies
        self.assertFalse(self.db.is_vacancy_sent(12345, 'vac_123'))
        self.db.mark_vacancy_sent(12345, 'vac_123')
        self.assertTrue(self.db.is_vacancy_sent(12345, 'vac_123'))
        
        # Test processed vacancies
        self.assertFalse(self.db.is_vacancy_processed(12345, 'vac_456'))
        self.db.mark_vacancy_processed(12345, 'vac_456')
        self.assertTrue(self.db.is_vacancy_processed(12345, 'vac_456'))
    
    def test_monitoring_state(self):
        """Test monitoring state management"""
        self.db.get_or_create_user(12345, 'testuser')
        
        # Initial state
        state = self.db.get_monitoring_state(12345)
        self.assertEqual(state['monitoring_enabled'], False)
        
        # Enable monitoring
        self.db.update_monitoring_state(12345, enabled=True)
        state = self.db.get_monitoring_state(12345)
        self.assertEqual(state['monitoring_enabled'], True)
        
        # Update last check
        now = datetime.now()
        self.db.update_monitoring_state(12345, last_check=now)
        state = self.db.get_monitoring_state(12345)
        self.assertIsNotNone(state['last_check'])
    
    def test_application_logging(self):
        """Test application logging"""
        self.db.get_or_create_user(12345, 'testuser')
        
        # Log application
        self.db.log_application(
            chat_id=12345,
            vacancy_id='vac_123',
            vacancy_title='Python Developer',
            company_name='Test Company',
            cover_letter='Test letter',
            status='success'
        )
        
        # Get applications count
        count = self.db.get_applications_count(12345)
        self.assertEqual(count, 1)
        
        # Get recent applications
        recent = self.db.get_recent_applications(12345, limit=5)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]['vacancy_id'], 'vac_123')
        self.assertEqual(recent[0]['status'], 'success')


if __name__ == '__main__':
    unittest.main()
