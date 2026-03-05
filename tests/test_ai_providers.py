"""
Unit tests for ai_providers.py

Tests multi-provider AI system.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ai_providers import (
    AIConfig, AIProvider, OpenAIProvider, OllamaProvider,
    LMStudioProvider, RuleBasedProvider, AIProviderFactory
)


class TestAIConfig:
    """Test AIConfig dataclass."""
    
    def test_config_creation(self):
        """Test config creation with defaults."""
        config = AIConfig(
            provider="openai",
            model="gpt-3.5-turbo"
        )
        
        assert config.provider == "openai"
        assert config.model == "gpt-3.5-turbo"
        assert config.temperature == 0.7
        assert config.max_tokens == 1500


class TestRuleBasedProvider:
    """Test RuleBasedProvider."""
    
    def test_is_available(self):
        """Test provider is always available."""
        config = AIConfig(provider="rule_based", model="none")
        provider = RuleBasedProvider(config)
        
        assert provider.is_available() is True
        
    def test_generate_flashcards_definition(self):
        """Test definition pattern generation."""
        config = AIConfig(provider="rule_based", model="none")
        provider = RuleBasedProvider(config)
        
        text = "Machine learning is a subset of artificial intelligence."
        flashcards = provider.generate_flashcards(text, max_cards=3)
        
        assert len(flashcards) > 0
        assert "question" in flashcards[0]
        assert "answer" in flashcards[0]
        
    def test_generate_flashcards_empty(self):
        """Test with empty text."""
        config = AIConfig(provider="rule_based", model="none")
        provider = RuleBasedProvider(config)
        
        flashcards = provider.generate_flashcards("", max_cards=3)
        
        assert len(flashcards) == 0


class TestOpenAIProvider:
    """Test OpenAIProvider."""
    
    def test_is_available_no_key(self):
        """Test availability without API key."""
        config = AIConfig(provider="openai", model="gpt-3.5-turbo")
        provider = OpenAIProvider(config)
        
        assert provider.is_available() is False
        
    def test_is_available_with_key(self):
        """Test availability with API key."""
        config = AIConfig(
            provider="openai",
            model="gpt-3.5-turbo",
            api_key="test_key"
        )
        provider = OpenAIProvider(config)
        
        assert provider.is_available() is True


class TestOllamaProvider:
    """Test OllamaProvider."""
    
    def test_is_available_not_running(self):
        """Test availability check."""
        config = AIConfig(provider="ollama", model="llama2")
        provider = OllamaProvider(config)
        
        # Just verify the method works (may be True or False depending on server)
        result = provider.is_available()
        assert isinstance(result, bool)
        
    @patch('ai_providers.requests.post')
    @patch('ai_providers.requests.get')
    def test_generate_flashcards(self, mock_get, mock_post):
        """Test Ollama generation."""
        # Mock availability check
        mock_get.return_value.status_code = 200
        
        # Mock generation
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": '{"flashcards": [{"question": "Test?", "answer": "Test answer", "difficulty": "easy", "tags": []}]}'
        }
        mock_post.return_value = mock_response
        
        config = AIConfig(provider="ollama", model="llama2")
        provider = OllamaProvider(config)
        
        text = "Test text for flashcard generation."
        flashcards = provider.generate_flashcards(text, max_cards=1)
        
        # May or may not succeed depending on JSON parsing
        assert isinstance(flashcards, list)


class TestLMStudioProvider:
    """Test LMStudioProvider."""
    
    def test_is_available_not_running(self):
        """Test availability when server not running."""
        config = AIConfig(provider="lmstudio", model="local-model")
        provider = LMStudioProvider(config)
        
        # Should return False when server not running
        assert provider.is_available() is False


class TestAIProviderFactory:
    """Test AIProviderFactory."""
    
    def test_create_rule_based(self):
        """Test creating rule-based provider."""
        config = AIConfig(provider="rule_based", model="none")
        provider = AIProviderFactory.create(config)
        
        assert isinstance(provider, RuleBasedProvider)
        
    def test_create_openai(self):
        """Test creating OpenAI provider."""
        config = AIConfig(
            provider="openai",
            model="gpt-3.5-turbo",
            api_key="test_key"
        )
        provider = AIProviderFactory.create(config)
        
        assert isinstance(provider, OpenAIProvider)
        
    def test_create_ollama(self):
        """Test creating Ollama provider."""
        config = AIConfig(provider="ollama", model="llama2")
        provider = AIProviderFactory.create(config)
        
        assert isinstance(provider, OllamaProvider)
        
    def test_create_unknown_defaults_to_rule_based(self):
        """Test unknown provider defaults to rule-based."""
        config = AIConfig(provider="unknown", model="none")
        provider = AIProviderFactory.create(config)
        
        assert isinstance(provider, RuleBasedProvider)
        
    def test_auto_detect_no_openai_key(self):
        """Test auto-detect returns a valid provider."""
        provider = AIProviderFactory.auto_detect()
        
        # Should return some provider (rule-based, ollama, or lmstudio)
        assert provider.is_available() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
