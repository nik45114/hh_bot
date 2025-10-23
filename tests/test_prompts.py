"""
Unit tests for prompt handling
"""
import unittest
from prompts import get_default_prompt


class TestPrompts(unittest.TestCase):
    """Test prompt generation"""
    
    def test_get_it_prompt(self):
        """Test getting IT domain prompt"""
        prompt = get_default_prompt('IT')
        
        self.assertIsNotNone(prompt)
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 100)
        # Should contain IT-related keywords
        self.assertTrue(
            any(keyword in prompt.lower() for keyword in ['технолог', 'разработ', 'опыт', 'проект'])
        )
    
    def test_get_management_prompt(self):
        """Test getting Management domain prompt"""
        prompt = get_default_prompt('Management')
        
        self.assertIsNotNone(prompt)
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 100)
        # Should contain management-related keywords
        self.assertTrue(
            any(keyword in prompt.lower() for keyword in ['команд', 'управлен', 'лидер', 'опыт'])
        )
    
    def test_get_default_prompt_unknown_domain(self):
        """Test getting prompt for unknown domain"""
        prompt = get_default_prompt('Unknown')
        
        # Should return a default prompt
        self.assertIsNotNone(prompt)
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 50)
    
    def test_prompt_structure(self):
        """Test that prompts have proper structure"""
        for domain in ['IT', 'Management', 'Other']:
            prompt = get_default_prompt(domain)
            
            # Should not be empty
            self.assertGreater(len(prompt), 50)
            # Should be string
            self.assertIsInstance(prompt, str)
            # Should not contain template errors
            self.assertNotIn('{{', prompt)
            self.assertNotIn('}}', prompt)


if __name__ == '__main__':
    unittest.main()
