"""
Unit tests for batch_processor.py

Tests batch processing capabilities.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch
from batch_processor import BatchProcessor, BatchJob, ClipboardBatchCollector
from flashcard_generator import FlashcardGenerator


class TestBatchProcessor:
    """Test BatchProcessor class."""
    
    def test_initialization(self):
        """Test processor initialization."""
        generator = FlashcardGenerator(provider="rule_based")
        processor = BatchProcessor(
            flashcard_generator=generator,
            max_workers=2,
            batch_size=5
        )
        
        assert processor.max_workers == 2
        assert processor.batch_size == 5
        
    def test_process_texts_single(self):
        """Test processing single text."""
        generator = FlashcardGenerator(provider="rule_based")
        processor = BatchProcessor(flashcard_generator=generator)
        
        texts = ["Machine learning is a subset of AI."]
        results = processor.process_texts(texts)
        
        assert results["total_texts"] == 1
        assert results["processed"] == 1
        assert "flashcards" in results
        
    def test_process_texts_multiple(self):
        """Test processing multiple texts."""
        generator = FlashcardGenerator(provider="rule_based")
        processor = BatchProcessor(flashcard_generator=generator)
        
        texts = [
            "Machine learning is a subset of AI.",
            "Python is a programming language.",
            "Deep learning is a subset of machine learning."
        ]
        results = processor.process_texts(texts)
        
        assert results["total_texts"] == 3
        assert results["processed"] == 3
        
    def test_process_texts_with_progress_callback(self):
        """Test progress callback."""
        generator = FlashcardGenerator(provider="rule_based")
        
        progress_calls = []
        def on_progress(current, total):
            progress_calls.append((current, total))
            
        processor = BatchProcessor(
            flashcard_generator=generator,
            on_progress=on_progress
        )
        
        texts = ["Test text one.", "Test text two."]
        processor.process_texts(texts)
        
        assert len(progress_calls) > 0
        
    def test_process_file_not_found(self):
        """Test processing non-existent file."""
        generator = FlashcardGenerator(provider="rule_based")
        processor = BatchProcessor(flashcard_generator=generator)
        
        results = processor.process_file("/nonexistent/file.txt")
        
        assert "error" in results
        
    def test_process_file_success(self):
        """Test processing existing file."""
        generator = FlashcardGenerator(provider="rule_based")
        processor = BatchProcessor(flashcard_generator=generator)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Machine learning is a subset of AI.\n")
            f.write("Python is a programming language.\n")
            temp_path = f.name
            
        try:
            results = processor.process_file(temp_path, chunk_size=100)
            
            assert "error" not in results or "flashcards" in results
        finally:
            os.unlink(temp_path)
            
    def test_process_directory_not_found(self):
        """Test processing non-existent directory."""
        generator = FlashcardGenerator(provider="rule_based")
        processor = BatchProcessor(flashcard_generator=generator)
        
        results = processor.process_directory("/nonexistent/directory")
        
        assert "error" in results
        
    def test_split_into_chunks(self):
        """Test text chunking."""
        generator = FlashcardGenerator(provider="rule_based")
        processor = BatchProcessor(flashcard_generator=generator)
        
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = processor._split_into_chunks(text, chunk_size=30)
        
        assert len(chunks) > 0
        assert all(len(chunk) <= 40 for chunk in chunks)  # Allow some flexibility


class TestClipboardBatchCollector:
    """Test ClipboardBatchCollector class."""
    
    def test_initialization(self):
        """Test collector initialization."""
        collector = ClipboardBatchCollector(
            time_window=300,
            similarity_threshold=0.8
        )
        
        assert collector.time_window == 300
        assert collector.similarity_threshold == 0.8
        
    def test_add_text(self):
        """Test adding text to collection."""
        collector = ClipboardBatchCollector()
        
        result = collector.add_text("Test text one")
        
        assert result is True
        assert len(collector.collected_texts) == 1
        
    def test_add_duplicate_text(self):
        """Test adding duplicate text."""
        collector = ClipboardBatchCollector(similarity_threshold=0.9)
        
        collector.add_text("Test text one")
        result = collector.add_text("Test text one")
        
        assert result is False
        assert len(collector.collected_texts) == 1
        
    def test_get_batch(self):
        """Test getting batch."""
        collector = ClipboardBatchCollector()
        
        collector.add_text("Text one")
        collector.add_text("Text two")
        
        batch = collector.get_batch(clear=True)
        
        assert len(batch) == 2
        assert len(collector.collected_texts) == 0  # Cleared
        
    def test_get_batch_no_clear(self):
        """Test getting batch without clearing."""
        collector = ClipboardBatchCollector()
        
        collector.add_text("Text one")
        
        batch = collector.get_batch(clear=False)
        
        assert len(batch) == 1
        assert len(collector.collected_texts) == 1  # Not cleared
        
    def test_is_similar_identical(self):
        """Test similarity check with identical texts."""
        collector = ClipboardBatchCollector(similarity_threshold=0.8)
        
        result = collector._is_similar("Hello world", "Hello world")
        
        assert result is True
        
    def test_is_similar_different(self):
        """Test similarity check with different texts."""
        collector = ClipboardBatchCollector(similarity_threshold=0.8)
        
        result = collector._is_similar("Hello world", "Completely different text")
        
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
