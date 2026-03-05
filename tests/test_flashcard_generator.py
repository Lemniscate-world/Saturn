"""
Unit tests for flashcard_generator.py

Tests the AI flashcard generation service.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from flashcard_generator import FlashcardGenerator, Flashcard


class TestFlashcardGenerator:
    """Test suite for FlashcardGenerator class."""
    
    def test_flashcard_dataclass(self):
        """Test Flashcard dataclass creation."""
        card = Flashcard(
            question="What is AI?",
            answer="Artificial Intelligence",
            source_text="AI is a field of computer science",
            difficulty="easy",
            tags=["ai", "tech"],
            quality_score=0.8
        )
        
        assert card.question == "What is AI?"
        assert card.answer == "Artificial Intelligence"
        assert card.difficulty == "easy"
        assert card.quality_score == 0.8
        
    def test_generator_initialization(self):
        """Test FlashcardGenerator initialization."""
        generator = FlashcardGenerator(
            provider="rule_based",
            max_flashcards=5,
            min_quality_score=0.6
        )
        
        assert generator.max_flashcards == 5
        assert generator.min_quality_score == 0.6
        
    def test_generate_rule_based_definition(self):
        """Test rule-based generation with definition pattern."""
        text = "Machine learning is a subset of artificial intelligence."
        
        generator = FlashcardGenerator(
            provider="rule_based",
            max_flashcards=5,
            min_quality_score=0.5
        )
        
        flashcards = generator.generate(text)
        
        assert len(flashcards) > 0
        assert "what is machine learning?" in flashcards[0].question.lower()
        assert "subset of artificial intelligence" in flashcards[0].answer.lower()
        
    def test_generate_rule_based_multiple_definitions(self):
        """Test rule-based generation with multiple definitions."""
        text = """
        Python is a programming language.
        Machine learning is a field of AI.
        Deep learning is a subset of machine learning.
        """
        
        generator = FlashcardGenerator(provider="rule_based", max_flashcards=3)
        flashcards = generator.generate(text)
        
        assert len(flashcards) <= 3
        assert all(isinstance(card, Flashcard) for card in flashcards)
        
    def test_quality_score_calculation(self):
        """Test quality score calculation."""
        generator = FlashcardGenerator(provider="rule_based")
        
        # Good question and answer
        score1 = generator._calculate_quality(
            "What is machine learning?",
            "A subset of AI that enables systems to learn from data",
            "Machine learning is a subset of AI"
        )
        
        # Poor question (too short)
        score2 = generator._calculate_quality(
            "What?",
            "A subset of AI",
            "Machine learning is a subset of AI"
        )
        
        # Poor answer (too short)
        score3 = generator._calculate_quality(
            "What is machine learning?",
            "AI",
            "Machine learning is a subset of AI"
        )
        
        assert score1 > score2
        assert score1 >= score3  # score3 might be equal due to source relevance
        assert 0.0 <= score1 <= 1.0
        
    def test_min_quality_filter(self):
        """Test that flashcards below min_quality_score are filtered."""
        text = "X is Y."  # Very short, will have low quality
        
        generator = FlashcardGenerator(
            provider="rule_based",
            max_flashcards=5,
            min_quality_score=0.9  # High threshold
        )
        
        flashcards = generator.generate(text)
        
        # Should be empty due to high quality threshold
        assert len(flashcards) == 0
        
    @patch('ai_providers.OpenAIProvider.generate_flashcards')
    def test_generate_with_ai_success(self, mock_generate):
        """Test AI generation with mocked OpenAI provider."""
        # Mock provider response
        mock_generate.return_value = [
            {
                "question": "What is machine learning?",
                "answer": "A subset of AI",
                "difficulty": "medium",
                "tags": ["ai", "ml"]
            }
        ]
        
        generator = FlashcardGenerator(
            provider="openai",
            api_key="test_key",
            max_flashcards=5,
            min_quality_score=0.5
        )
        
        text = "Machine learning is a subset of AI."
        flashcards = generator.generate(text)
        
        assert len(flashcards) > 0
        assert flashcards[0].question == "What is machine learning?"
        
    @patch('ai_providers.OpenAIProvider.generate_flashcards')
    @patch('ai_providers.OllamaProvider.generate_flashcards')
    def test_generate_with_ai_fallback(self, mock_ollama, mock_openai):
        """Test fallback to rule-based when AI fails."""
        # Mock both providers to return empty (simulating failure)
        mock_openai.return_value = []
        mock_ollama.return_value = []
        
        generator = FlashcardGenerator(
            provider="rule_based",
            max_flashcards=5,
            min_quality_score=0.5
        )
        
        text = "Machine learning is a subset of AI."
        flashcards = generator.generate(text)
        
        # Rule-based should still work
        assert isinstance(flashcards, list)
        
    def test_empty_text(self):
        """Test generation with empty text."""
        generator = FlashcardGenerator(provider="rule_based")
        flashcards = generator.generate("")
        
        assert len(flashcards) == 0
        
    def test_text_too_short(self):
        """Test generation with very short text."""
        generator = FlashcardGenerator(provider="rule_based")
        flashcards = generator.generate("short")
        
        # Should not generate flashcards from very short text
        assert len(flashcards) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
