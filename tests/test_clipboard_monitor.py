"""
Unit tests for clipboard_monitor.py

Tests the clipboard monitoring service functionality.
"""

import pytest
import time
from unittest.mock import Mock, patch
from clipboard_monitor import ClipboardMonitor, ClipboardEvent


class TestClipboardMonitor:
    """Test suite for ClipboardMonitor class."""
    
    def test_clipboard_event_creation(self):
        """Test ClipboardEvent dataclass creation."""
        event = ClipboardEvent(
            text="Test text",
            timestamp=time.time(),
            source_app="test_app"
        )
        
        assert event.text == "Test text"
        assert event.timestamp > 0
        assert event.source_app == "test_app"
        
    def test_monitor_initialization(self):
        """Test ClipboardMonitor initialization with default parameters."""
        monitor = ClipboardMonitor()
        
        assert monitor.poll_interval == 0.5
        assert monitor.min_text_length == 10
        assert monitor._running is False
        assert monitor._thread is None
        
    def test_monitor_custom_parameters(self):
        """Test ClipboardMonitor with custom parameters."""
        callback = Mock()
        monitor = ClipboardMonitor(
            poll_interval=1.0,
            min_text_length=20,
            on_text_captured=callback
        )
        
        assert monitor.poll_interval == 1.0
        assert monitor.min_text_length == 20
        assert monitor.on_text_captured == callback
        
    @patch('clipboard_monitor.pyperclip.paste')
    def test_capture_now_success(self, mock_paste):
        """Test manual capture with valid text."""
        mock_paste.return_value = "This is a test text that is long enough"
        
        monitor = ClipboardMonitor(min_text_length=10)
        event = monitor.capture_now()
        
        assert event is not None
        assert event.text == "This is a test text that is long enough"
        assert event.timestamp > 0
        
    @patch('clipboard_monitor.pyperclip.paste')
    def test_capture_now_too_short(self, mock_paste):
        """Test manual capture with text too short."""
        mock_paste.return_value = "short"
        
        monitor = ClipboardMonitor(min_text_length=10)
        event = monitor.capture_now()
        
        assert event is None
        
    @patch('clipboard_monitor.pyperclip.paste')
    def test_capture_now_empty(self, mock_paste):
        """Test manual capture with empty clipboard."""
        mock_paste.return_value = ""
        
        monitor = ClipboardMonitor()
        event = monitor.capture_now()
        
        assert event is None
        
    def test_start_stop_monitor(self):
        """Test starting and stopping monitor."""
        monitor = ClipboardMonitor()
        
        # Start monitor
        monitor.start()
        assert monitor._running is True
        assert monitor._thread is not None
        
        # Stop monitor
        monitor.stop()
        assert monitor._running is False
        assert monitor._thread is None
        
    def test_callback_triggered(self):
        """Test that callback is triggered on text capture."""
        callback = Mock()
        monitor = ClipboardMonitor(
            poll_interval=0.1,
            min_text_length=5,
            on_text_captured=callback
        )
        
        with patch('clipboard_monitor.pyperclip.paste') as mock_paste:
            # Initial clipboard content
            mock_paste.return_value = "initial"
            monitor._last_clipboard_content = "initial"
            
            # Start monitor
            monitor.start()
            
            # Simulate clipboard change
            mock_paste.return_value = "new text content"
            time.sleep(0.3)  # Wait for monitor to detect change
            
            # Stop monitor
            monitor.stop()
            
            # Callback should have been called
            assert callback.called
            assert callback.call_args[0][0].text == "new text content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
