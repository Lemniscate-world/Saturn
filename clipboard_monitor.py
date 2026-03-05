"""
Clipboard Monitoring Service for Echo Desktop Application.

This service monitors the system clipboard for text selections and triggers
flashcard generation when user selects text anywhere on their computer.

Architecture: Adapter (Spoke) - connects external clipboard to core business logic.
"""

import time
import threading
import pyperclip
from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class ClipboardEvent:
    """Represents a clipboard text selection event."""
    text: str
    timestamp: float
    source_app: Optional[str] = None  # Future: detect source application


class ClipboardMonitor:
    """
    Monitors system clipboard for text changes.
    
    Uses polling mechanism to detect clipboard changes every N seconds.
    Optimized to minimize CPU usage while maintaining responsiveness.
    
    Cross-platform: Works on Windows, macOS, and Linux.
    """
    
    def __init__(
        self, 
        poll_interval: float = 0.5,
        min_text_length: int = 10,
        on_text_captured: Optional[Callable[[ClipboardEvent], None]] = None
    ):
        """
        Initialize clipboard monitor.
        
        Args:
            poll_interval: Time in seconds between clipboard checks (default: 0.5s)
            min_text_length: Minimum text length to trigger capture (default: 10 chars)
            on_text_captured: Callback function when text is captured
        """
        self.poll_interval = poll_interval
        self.min_text_length = min_text_length
        self.on_text_captured = on_text_captured
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_clipboard_content = ""
        
    def start(self):
        """Start monitoring clipboard in background thread."""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        """Stop monitoring clipboard."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
            
    def _monitor_loop(self):
        """Main monitoring loop - runs in background thread."""
        # Initialize with current clipboard content
        try:
            self._last_clipboard_content = pyperclip.paste()
        except Exception:
            self._last_clipboard_content = ""
            
        while self._running:
            try:
                # Check clipboard for new content
                current_content = pyperclip.paste()
                
                # Detect if content changed and meets minimum length
                if (current_content != self._last_clipboard_content and 
                    len(current_content) >= self.min_text_length):
                    
                    # Create clipboard event
                    event = ClipboardEvent(
                        text=current_content,
                        timestamp=time.time()
                    )
                    
                    # Update last content
                    self._last_clipboard_content = current_content
                    
                    # Trigger callback if set
                    if self.on_text_captured:
                        self.on_text_captured(event)
                        
            except Exception as e:
                # Log error but continue monitoring
                print(f"Clipboard monitoring error: {e}")
                
            # Sleep before next check
            time.sleep(self.poll_interval)
            
    def capture_now(self) -> Optional[ClipboardEvent]:
        """
        Manually capture current clipboard content.
        
        Returns:
            ClipboardEvent if text exists, None otherwise
        """
        try:
            content = pyperclip.paste()
            if len(content) >= self.min_text_length:
                return ClipboardEvent(
                    text=content,
                    timestamp=time.time()
                )
        except Exception as e:
            print(f"Manual capture error: {e}")
            
        return None


# Example usage and testing
if __name__ == "__main__":
    def on_text_captured(event: ClipboardEvent):
        print(f"\n=== Text Captured ===")
        print(f"Time: {time.strftime('%H:%M:%S', time.localtime(event.timestamp))}")
        print(f"Length: {len(event.text)} characters")
        print(f"Preview: {event.text[:100]}...")
        print("=" * 40)
    
    print("Starting clipboard monitor...")
    print("Select text anywhere and copy it (Ctrl+C / Cmd+C)")
    print("Press Ctrl+C to stop\n")
    
    monitor = ClipboardMonitor(
        poll_interval=0.5,
        min_text_length=10,
        on_text_captured=on_text_captured
    )
    
    monitor.start()
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        monitor.stop()
        print("Monitor stopped.")
