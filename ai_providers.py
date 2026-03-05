"""
Advanced AI Integration for Echo Desktop Application.

Supports multiple AI backends:
- OpenAI GPT models (cloud)
- Local LLM via Ollama (privacy-focused)
- LM Studio (local GUI)
- Rule-based fallback (no external dependencies)

Architecture: Adapter (Spoke) - abstracts AI provider differences.
"""

import os
import json
import requests
from typing import List, Dict, Optional, Protocol
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class AIConfig:
    """Configuration for AI backend."""
    provider: str  # "openai", "ollama", "lmstudio", "rule_based"
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1500


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    def generate_flashcards(self, text: str, max_cards: int = 5) -> List[Dict]:
        """Generate flashcards from text."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI GPT models provider."""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        
    def is_available(self) -> bool:
        return self.api_key is not None
        
    def generate_flashcards(self, text: str, max_cards: int = 5) -> List[Dict]:
        """Generate flashcards using OpenAI API."""
        import openai
        
        openai.api_key = self.api_key
        
        prompt = f"""Generate {max_cards} flashcards from the following text.
Each flashcard should have a clear question and concise answer.

Format your response as JSON:
{{
    "flashcards": [
        {{
            "question": "Question text here?",
            "answer": "Answer text here",
            "difficulty": "easy|medium|hard",
            "tags": ["tag1", "tag2"]
        }}
    ]
}}

Text to convert:
{text}

Generate flashcards that test key concepts, definitions, and important facts.
Questions should be clear and unambiguous.
Answers should be concise but complete."""

        response = openai.ChatCompletion.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "You are an expert educator who creates high-quality flashcards for spaced repetition learning."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        
        content = response.choices[0].message.content
        
        try:
            data = json.loads(content)
            return data.get("flashcards", [])
        except json.JSONDecodeError:
            return []


class OllamaProvider(AIProvider):
    """Local LLM provider via Ollama."""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.base_url = config.base_url or "http://localhost:11434"
        
    def is_available(self) -> bool:
        """Check if Ollama server is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
            
    def generate_flashcards(self, text: str, max_cards: int = 5) -> List[Dict]:
        """Generate flashcards using Ollama API."""
        
        prompt = f"""Generate {max_cards} flashcards from the following text.
Each flashcard should have a clear question and concise answer.

Format your response as JSON:
{{
    "flashcards": [
        {{
            "question": "Question text here?",
            "answer": "Answer text here",
            "difficulty": "easy|medium|hard",
            "tags": ["tag1", "tag2"]
        }}
    ]
}}

Text to convert:
{text}"""

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.config.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.config.temperature,
                        "num_predict": self.config.max_tokens
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json().get("response", "")
                
                # Extract JSON from response
                try:
                    # Try to find JSON in response
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    if start != -1 and end > start:
                        json_str = content[start:end]
                        data = json.loads(json_str)
                        return data.get("flashcards", [])
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Failed to parse JSON response: {e}")
                    
        except Exception as e:
            print(f"Ollama error: {e}")
            
        return []


class LMStudioProvider(AIProvider):
    """Local LLM provider via LM Studio."""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.base_url = config.base_url or "http://localhost:1234/v1"
        
    def is_available(self) -> bool:
        """Check if LM Studio server is running."""
        try:
            response = requests.get(f"{self.base_url}/models", timeout=2)
            return response.status_code == 200
        except:
            return False
            
    def generate_flashcards(self, text: str, max_cards: int = 5) -> List[Dict]:
        """Generate flashcards using LM Studio OpenAI-compatible API."""
        
        prompt = f"""Generate {max_cards} flashcards from the following text.
Format as JSON with "flashcards" array containing question, answer, difficulty, tags.

Text: {text}"""

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.config.model,
                    "messages": [
                        {"role": "system", "content": "You are an expert educator."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens
                },
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                
                try:
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    if start != -1 and end > start:
                        json_str = content[start:end]
                        data = json.loads(json_str)
                        return data.get("flashcards", [])
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Failed to parse JSON response: {e}")
                    
        except Exception as e:
            print(f"LM Studio error: {e}")
            
        return []


class RuleBasedProvider(AIProvider):
    """Rule-based flashcard generation (no external dependencies)."""
    
    def __init__(self, config: AIConfig):
        self.config = config
        
    def is_available(self) -> bool:
        return True  # Always available
        
    def generate_flashcards(self, text: str, max_cards: int = 5) -> List[Dict]:
        """Generate flashcards using pattern matching."""
        
        flashcards = []
        
        # Definition patterns
        patterns = [
            (" is defined as ", "What is"),
            (" means ", "What does"),
            (" refers to ", "What does"),
            (" is a ", "What is"),
            (" are ", "What are")
        ]
        
        sentences = text.split(". ")
        
        for sentence in sentences[:max_cards]:
            for pattern, question_prefix in patterns:
                if pattern in sentence.lower():
                    parts = sentence.lower().split(pattern)
                    if len(parts) == 2:
                        term = parts[0].strip()
                        definition = parts[1].strip()
                        
                        flashcards.append({
                            "question": f"{question_prefix} {term}?",
                            "answer": definition,
                            "difficulty": "medium",
                            "tags": ["definition"]
                        })
                        break
                        
        return flashcards[:max_cards]


class AIProviderFactory:
    """Factory for creating AI providers."""
    
    @staticmethod
    def create(config: AIConfig) -> AIProvider:
        """Create appropriate AI provider based on config."""
        
        providers = {
            "openai": OpenAIProvider,
            "ollama": OllamaProvider,
            "lmstudio": LMStudioProvider,
            "rule_based": RuleBasedProvider
        }
        
        provider_class = providers.get(config.provider, RuleBasedProvider)
        return provider_class(config)
        
    @staticmethod
    def auto_detect() -> AIProvider:
        """Auto-detect best available provider."""
        
        # Try OpenAI first
        if os.getenv("OPENAI_API_KEY"):
            config = AIConfig(provider="openai", model="gpt-3.5-turbo")
            provider = OpenAIProvider(config)
            if provider.is_available():
                return provider
                
        # Try Ollama
        config = AIConfig(provider="ollama", model="llama2")
        provider = OllamaProvider(config)
        if provider.is_available():
            return provider
            
        # Try LM Studio
        config = AIConfig(provider="lmstudio", model="local-model")
        provider = LMStudioProvider(config)
        if provider.is_available():
            return provider
            
        # Fallback to rule-based
        config = AIConfig(provider="rule_based", model="none")
        return RuleBasedProvider(config)


# Example usage
if __name__ == "__main__":
    print("Testing AI Providers...")
    print("=" * 60)
    
    # Auto-detect best provider
    provider = AIProviderFactory.auto_detect()
    
    print(f"Using provider: {provider.__class__.__name__}")
    print(f"Available: {provider.is_available()}")
    
    # Test generation
    sample_text = """
    Machine learning is a subset of artificial intelligence.
    Neural networks are computing systems inspired by biological neural networks.
    Deep learning is a subset of machine learning using multi-layered networks.
    """
    
    flashcards = provider.generate_flashcards(sample_text, max_cards=3)
    
    print(f"\nGenerated {len(flashcards)} flashcards:\n")
    
    for i, card in enumerate(flashcards, 1):
        print(f"Card {i}:")
        print(f"  Q: {card.get('question')}")
        print(f"  A: {card.get('answer')}")
        print(f"  Difficulty: {card.get('difficulty')}")
        print(f"  Tags: {', '.join(card.get('tags', []))}")
        print()
