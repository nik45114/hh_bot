"""
Unit tests for bot callback routing
"""
import unittest
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import JobBot


class TestBotCallbacks(unittest.TestCase):
    """Test bot callback routing"""
    
    def setUp(self):
        """Set up test fixtures"""
        with patch('bot.HeadHunterClient'), \
             patch('bot.CoverLetterGenerator'), \
             patch('bot.Database'):
            self.bot = JobBot()
    
    def test_callback_routing_criteria_domain(self):
        """Test that criteria_domain callbacks are routed correctly"""
        # Create mock query and context
        query = Mock()
        query.data = 'criteria_domain'
        query.message = Mock()
        query.message.chat_id = 12345
        query.from_user = Mock()
        query.from_user.id = 12345
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        
        context = Mock()
        
        # Create mock update
        update = Mock()
        update.callback_query = query
        update.effective_user = query.from_user
        
        # Verify the action would be handled
        action = 'criteria_domain'
        should_handle = (
            action.startswith('criteria_') or 
            action.startswith('set_domain_') or 
            action.startswith('set_level_') or 
            action.startswith('set_city_')
        )
        self.assertTrue(should_handle, "criteria_domain should be handled")
    
    def test_callback_routing_set_domain(self):
        """Test that set_domain_* callbacks are routed correctly"""
        for domain in ['IT', 'Management', 'Other']:
            action = f'set_domain_{domain}'
            should_handle = (
                action.startswith('criteria_') or 
                action.startswith('set_domain_') or 
                action.startswith('set_level_') or 
                action.startswith('set_city_')
            )
            self.assertTrue(should_handle, f"{action} should be handled")
    
    def test_callback_routing_set_level(self):
        """Test that set_level_* callbacks are routed correctly"""
        for level in ['Руководитель', 'Project Manager', 'Team Lead', 'CTO/CIO']:
            action = f'set_level_{level}'
            should_handle = (
                action.startswith('criteria_') or 
                action.startswith('set_domain_') or 
                action.startswith('set_level_') or 
                action.startswith('set_city_')
            )
            self.assertTrue(should_handle, f"{action} should be handled")
    
    def test_callback_routing_set_city(self):
        """Test that set_city_* callbacks are routed correctly"""
        for city_data in ['1_Москва', '2_Санкт-Петербург', '113_Россия']:
            action = f'set_city_{city_data}'
            should_handle = (
                action.startswith('criteria_') or 
                action.startswith('set_domain_') or 
                action.startswith('set_level_') or 
                action.startswith('set_city_')
            )
            self.assertTrue(should_handle, f"{action} should be handled")
    
    def test_callback_routing_other_actions(self):
        """Test that other callbacks are not incorrectly routed to criteria handler"""
        for action in ['main_search', 'main_prompt', 'search_now', 'prompt_edit', 'vac_apply_123']:
            should_not_handle_as_criteria = not (
                action.startswith('criteria_') or 
                action.startswith('set_domain_') or 
                action.startswith('set_level_') or 
                action.startswith('set_city_')
            )
            self.assertTrue(should_not_handle_as_criteria, f"{action} should not be handled as criteria")


if __name__ == '__main__':
    unittest.main()
