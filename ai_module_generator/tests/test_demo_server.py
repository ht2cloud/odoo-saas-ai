"""
Tests for Demo Server Socket.IO functionality
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_module_generator.demo_server import app, socketio, handle_join_session


class TestDemoServerSocketIO(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
    def test_socket_io_imports(self):
        """Test that all required socketio functions are imported"""
        # This test will fail if join_room is not properly imported
        from flask_socketio import SocketIO, emit, join_room
        
        # Check that join_room is available in the module scope
        import ai_module_generator.demo_server as demo_module
        self.assertTrue(hasattr(demo_module, 'join_room'), 
                       "join_room should be imported from flask_socketio")

    @patch('ai_module_generator.demo_server.join_room')
    @patch('ai_module_generator.demo_server.emit')
    def test_handle_join_session(self, mock_emit, mock_join_room):
        """Test that handle_join_session works correctly"""
        # Mock data for the join session event
        test_data = {'session_id': 'test-session-123'}
        
        # Call the handler function
        handle_join_session(test_data)
        
        # Verify that join_room was called with the correct session ID
        mock_join_room.assert_called_once_with('test-session-123')
        
        # Verify that emit was called with the correct response
        mock_emit.assert_called_once_with('joined', {'session_id': 'test-session-123'})

    @patch('ai_module_generator.demo_server.join_room')
    @patch('ai_module_generator.demo_server.emit')
    def test_handle_join_session_no_session_id(self, mock_emit, mock_join_room):
        """Test that handle_join_session handles missing session_id gracefully"""
        # Mock data without session_id
        test_data = {}
        
        # Call the handler function
        handle_join_session(test_data)
        
        # Verify that join_room was NOT called
        mock_join_room.assert_not_called()
        
        # Verify that emit was NOT called
        mock_emit.assert_not_called()

    @patch('ai_module_generator.demo_server.join_room')
    @patch('ai_module_generator.demo_server.emit')
    def test_handle_join_session_empty_session_id(self, mock_emit, mock_join_room):
        """Test that handle_join_session handles empty session_id gracefully"""
        # Mock data with empty session_id
        test_data = {'session_id': ''}
        
        # Call the handler function
        handle_join_session(test_data)
        
        # Verify that join_room was NOT called
        mock_join_room.assert_not_called()
        
        # Verify that emit was NOT called
        mock_emit.assert_not_called()


if __name__ == '__main__':
    unittest.main()