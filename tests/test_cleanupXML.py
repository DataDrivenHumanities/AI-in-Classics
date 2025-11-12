import os
import sys
import unittest
import tempfile
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cleanupXML import cleanup_XML

class TestCleanupXML(unittest.TestCase):
    """Tests for the cleanup_XML function."""

    @patch('requests.get')
    def test_xml_parsing(self, mock_get):
        """Test the basic XML parsing functionality."""
        # Mock the response from requests.get
        mock_response = MagicMock()
        mock_response.text = """
        <?xml version="1.0" encoding="UTF-8"?>
        <TEI>
            <author>Test Author</author>
            <title>Test Title</title>
            <text>Sample Text Content</text>
        </TEI>
        """
        mock_get.return_value = mock_response
        
        # Call the function with a test URN
        result = cleanup_XML('urn:test:data:1234')
        
        # Check that the result contains our expected content
        self.assertIn('Test Author', result)
        self.assertIn('Test Title', result)
        self.assertIn('Sample Text Content', result)
    
    @patch('requests.get')
    def test_file_saving(self, mock_get):
        """Test that files are saved correctly."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.text = "<TEI><author>Author</author><title>Title</title><text>Text</text></TEI>"
        mock_get.return_value = mock_response
        
        # Create temporary directories for testing
        with tempfile.TemporaryDirectory() as raw_dir:
            with tempfile.TemporaryDirectory() as clean_dir:
                # Call the function with the temp directories
                cleanup_XML('urn:test:data:1234', save_raw_path=raw_dir, save_clean_path=clean_dir)
                
                # Check that files were created in both directories
                raw_files = os.listdir(raw_dir)
                clean_files = os.listdir(clean_dir)
                
                self.assertEqual(len(raw_files), 1, "Raw XML file was not created")
                self.assertEqual(len(clean_files), 1, "Cleaned XML file was not created")
    
    @patch('requests.get')
    def test_missing_elements(self, mock_get):
        """Test handling when XML elements are missing."""
        # Mock the response with missing elements
        mock_response = MagicMock()
        mock_response.text = "<TEI><text>Only Text</text></TEI>"
        mock_get.return_value = mock_response
        
        # Call the function
        result = cleanup_XML('urn:test:data:1234')
        
        # Check that the result still contains what's available
        self.assertIn('Only Text', result)
        self.assertNotIn('author', result.lower())  # Should not contain author tag
        self.assertNotIn('title', result.lower())   # Should not contain title tag
    
    @patch('requests.get')
    def test_error_handling(self, mock_get):
        """Test error handling for invalid directories."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.text = "<TEI><text>Test</text></TEI>"
        mock_get.return_value = mock_response
        
        # Call with non-existent directories
        result = cleanup_XML('urn:test:data:1234', 
                            save_raw_path='/nonexistent/path',
                            save_clean_path='/nonexistent/path')
        
        # Function should continue without error
        self.assertIn('Test', result)

if __name__ == '__main__':
    unittest.main()
