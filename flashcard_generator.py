"""
AI Flashcard Generation Service for Echo Desktop Application.

This service generates flashcards from selected text using AI (OpenAI or local LLM).
Implements smart question generation and context-aware answer extraction.

Architecture: Core (Hub) - pure business logic for flashcard generation.
"""

import os
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from ai_providers import AIProviderFactory, AIConfig


@dataclass
class Flashcard:
    """Represents a generated flashcard."""
    question: str
    answer: str
    source_text: str
    difficulty: str  # easy, medium, hard
    tags: List[str]
    quality_score: float  # 0.0 to 1.0


class FlashcardGenerator:
    """
    Generates flashcards from text using AI.
    
    Supports multiple AI backends:
    - OpenAI GPT models (requires API key)
    - Local LLM (Ollama, LM Studio, etc.)
    - Rule-based generation (fallback)
    
    Quality scoring ensures only high-quality flashcards are created.
    """
    
    def __init__(
        self,
        provider: str = "auto",
        model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        max_flashcards: int = 5,
        min_quality_score: float = 0.6
    ):
        """
        Initialize flashcard generator.
        
        Args:
            provider: AI provider ("auto", "openai", "ollama", "lmstudio", "rule_based")
            model: AI model to use
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            max_flashcards: Maximum flashcards to generate per text
            min_quality_score: Minimum quality score (0.0-1.0) to accept
        """
        self.max_flashcards = max_flashcards
        self.min_quality_score = min_quality_score
        
        # Create AI provider
        if provider == "auto":
            self.ai_provider = AIProviderFactory.auto_detect()
        else:
            config = AIConfig(
                provider=provider,
                model=model,
                api_key=api_key or os.getenv("OPENAI_API_KEY")
            )
            self.ai_provider = AIProviderFactory.create(config)
            
    def generate(self, text: str) -> List[Flashcard]:
        """
        Generate flashcards from text.
        
        Args:
            text: Source text to generate flashcards from
            
        Returns:
            List of Flashcard objects with quality score >= min_quality_score
        """
        if len(text) < 10:
            return []
            
        # Use AI provider to generate flashcards
        raw_flashcards = self.ai_provider.generate_flashcards(text, self.max_flashcards)
        
        # Convert to Flashcard objects with quality scoring
        flashcards = []
        for item in raw_flashcards:
            quality = self._calculate_quality(
                item.get("question", ""),
                item.get("answer", ""),
                text
            )
            
            if quality >= self.min_quality_score:
                flashcards.append(Flashcard(
                    question=item.get("question", ""),
                    answer=item.get("answer", ""),
                    source_text=text,
                    difficulty=item.get("difficulty", "medium"),
                    tags=item.get("tags", []),
                    quality_score=quality
                ))
                
        return flashcards
            
    def _calculate_quality(self, question: str, answer: str, source: str) -> float:
        """
        Calculate quality score for a flashcard.
        
        Factors:
        - Question clarity (length, structure)
        - Answer completeness (length, relevance)
        - Source coverage (answer present in source)
        
        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 1.0
        
        # Question quality checks
        if len(question) < 10:
            score -= 0.3  # Too short
        if len(question) > 200:
            score -= 0.2  # Too long
        if "?" not in question:
            score -= 0.1  # Missing question mark
            
        # Answer quality checks
        if len(answer) < 5:
            score -= 0.4  # Too short
        if len(answer) > 500:
            score -= 0.3  # Too long
            
        # Source relevance check
        if answer.lower() not in source.lower():
            score -= 0.2  # Answer not in source
            
        return max(0.0, min(1.0, score))


# Example usage
if __name__ == "__main__":
    # Test with sample text
    sample_text = """
    Machine learning is a subset of artificial intelligence that enables 
    systems to learn and improve from experience without being explicitly programmed.
    Neural networks are computing systems inspired by biological neural networks.
    Deep learning is a subset of machine learning that uses multi-layered neural networks.
    """
    
    print("Testing Flashcard Generator...")
    print("=" * 60)
    
    # Test without API key (rule-based fallback)
    generator = FlashcardGenerator(
        max_flashcards=5,
        min_quality_score=0.5
    )
    
    flashcards = generator.generate(sample_text)
    
    print(f"\nGenerated {len(flashcards)} flashcards:\n")
    
    for i, card in enumerate(flashcards, 1):
        print(f"Flashcard {i}:")
        print(f"  Q: {card.question}")
        print(f"  A: {card.answer}")
        print(f"  Difficulty: {card.difficulty}")
        print(f"  Quality: {card.quality_score:.2f}")
        print(f"  Tags: {', '.join(card.tags)}")
        print()
