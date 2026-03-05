"""
Smart Question Generation Templates for Echo Desktop Application.

Implements context-aware question generation with multiple question types:
- Definition questions (What is X?)
- Comparison questions (Difference between X and Y?)
- Process questions (How does X work?)
- Application questions (When would you use X?)
- Causal questions (Why does X happen?)

Architecture: Core (Hub) - pure question generation logic.
"""

from typing import List, Dict, Tuple
import re
from dataclasses import dataclass


@dataclass
class QuestionTemplate:
    """Template for generating questions."""
    question_type: str
    pattern: str
    template: str
    difficulty: str


class SmartQuestionGenerator:
    """
    Generates intelligent questions from text using pattern matching
    and context analysis.
    
    Question Types:
    1. Definition: "What is [term]?"
    2. Comparison: "What is the difference between [A] and [B]?"
    3. Process: "How does [process] work?"
    4. Application: "When would you use [concept]?"
    5. Causal: "Why does [phenomenon] occur?"
    """
    
    def __init__(self):
        self.templates = self._load_templates()
        
    def _load_templates(self) -> List[QuestionTemplate]:
        """Load question templates."""
        return [
            # Definition patterns
            QuestionTemplate(
                question_type="definition",
                pattern=r"(\w+(?:\s+\w+)?)\s+is\s+(?:defined\s+as|a|an)\s+(.+)",
                template="What is {term}?",
                difficulty="easy"
            ),
            QuestionTemplate(
                question_type="definition",
                pattern=r"(\w+(?:\s+\w+)?)\s+means\s+(.+)",
                template="What does {term} mean?",
                difficulty="easy"
            ),
            QuestionTemplate(
                question_type="definition",
                pattern=r"(\w+(?:\s+\w+)?)\s+refers\s+to\s+(.+)",
                template="What does {term} refer to?",
                difficulty="easy"
            ),
            
            # Process patterns
            QuestionTemplate(
                question_type="process",
                pattern=r"(\w+(?:\s+\w+)?)\s+works\s+by\s+(.+)",
                template="How does {term} work?",
                difficulty="medium"
            ),
            QuestionTemplate(
                question_type="process",
                pattern=r"(\w+(?:\s+\w+)?)\s+process\s+involves\s+(.+)",
                template="What does the {term} process involve?",
                difficulty="medium"
            ),
            
            # Comparison patterns
            QuestionTemplate(
                question_type="comparison",
                pattern=r"(\w+(?:\s+\w+)?)\s+(?:vs|versus|compared\s+to)\s+(\w+(?:\s+\w+)?)",
                template="What is the difference between {term1} and {term2}?",
                difficulty="medium"
            ),
            
            # Causal patterns
            QuestionTemplate(
                question_type="causal",
                pattern=r"(\w+(?:\s+\w+)?)\s+(?:causes|leads\s+to|results\s+in)\s+(.+)",
                template="Why does {term} occur?",
                difficulty="hard"
            ),
            
            # Application patterns
            QuestionTemplate(
                question_type="application",
                pattern=r"(\w+(?:\s+\w+)?)\s+is\s+used\s+(?:for|to|in)\s+(.+)",
                template="When would you use {term}?",
                difficulty="medium"
            ),
        ]
        
    def generate_questions(self, text: str, max_questions: int = 5) -> List[Dict]:
        """
        Generate questions from text using pattern matching.
        
        Args:
            text: Source text to generate questions from
            max_questions: Maximum number of questions to generate
            
        Returns:
            List of question dictionaries with question, answer, type, difficulty
        """
        questions = []
        sentences = self._split_sentences(text)
        
        for sentence in sentences:
            if len(questions) >= max_questions:
                break
                
            for template in self.templates:
                match = re.search(template.pattern, sentence, re.IGNORECASE)
                
                if match:
                    question_data = self._create_question(
                        sentence, match, template
                    )
                    
                    if question_data:
                        questions.append(question_data)
                        break
                        
        return questions
        
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Split on sentence boundaries
        sentences = re.split(r'[.!?]+', text)
        # Clean and filter
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        return sentences
        
    def _create_question(
        self, 
        sentence: str, 
        match: re.Match, 
        template: QuestionTemplate
    ) -> Dict:
        """Create question from match."""
        
        groups = match.groups()
        
        if len(groups) >= 2:
            term = groups[0].strip()
            answer = groups[1].strip()
            
            # Format question
            question = template.template.format(
                term=term,
                term1=term,
                term2=groups[1].strip() if len(groups) > 2 else ""
            )
            
            return {
                "question": question,
                "answer": answer,
                "question_type": template.question_type,
                "difficulty": template.difficulty,
                "source_sentence": sentence
            }
            
        return None
        
    def analyze_text_context(self, text: str) -> Dict:
        """
        Analyze text to determine optimal question types.
        
        Returns:
            Dictionary with context analysis results
        """
        analysis = {
            "total_sentences": len(self._split_sentences(text)),
            "has_definitions": bool(re.search(r'\b(is|means|refers to)\b', text, re.IGNORECASE)),
            "has_processes": bool(re.search(r'\b(works by|process|steps)\b', text, re.IGNORECASE)),
            "has_comparisons": bool(re.search(r'\b(vs|versus|compared to|difference)\b', text, re.IGNORECASE)),
            "has_causal": bool(re.search(r'\b(causes|leads to|results in|because)\b', text, re.IGNORECASE)),
            "recommended_types": []
        }
        
        # Recommend question types based on content
        if analysis["has_definitions"]:
            analysis["recommended_types"].append("definition")
        if analysis["has_processes"]:
            analysis["recommended_types"].append("process")
        if analysis["has_comparisons"]:
            analysis["recommended_types"].append("comparison")
        if analysis["has_causal"]:
            analysis["recommended_types"].append("causal")
            
        return analysis


class ContextAwareAnswerExtractor:
    """
    Extracts context-aware answers from text.
    
    Features:
    - Identifies key terms and definitions
    - Extracts complete sentences as answers
    - Handles multi-sentence contexts
    - Preserves important context
    """
    
    def extract_answer(self, text: str, question: str, question_type: str) -> str:
        """
        Extract appropriate answer from text for a given question.
        
        Args:
            text: Source text
            question: Question to answer
            question_type: Type of question (definition, process, etc.)
            
        Returns:
            Extracted answer string
        """
        
        if question_type == "definition":
            return self._extract_definition(text, question)
        elif question_type == "process":
            return self._extract_process(text, question)
        elif question_type == "comparison":
            return self._extract_comparison(text, question)
        elif question_type == "causal":
            return self._extract_causal(text, question)
        else:
            return self._extract_generic(text, question)
            
    def _extract_definition(self, text: str, question: str) -> str:
        """Extract definition answer."""
        # Extract term from question
        term_match = re.search(r'What is (.+)\?', question)
        
        if term_match:
            term = term_match.group(1).strip().lower()
            
            # Find definition in text
            patterns = [
                rf"{term}\s+is\s+(.+?)(?:\.|,)",
                rf"{term}\s+means\s+(.+?)(?:\.|,)",
                rf"{term}\s+refers\s+to\s+(.+?)(?:\.|,)"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
                    
        return ""
        
    def _extract_process(self, text: str, question: str) -> str:
        """Extract process description."""
        # Find process-related sentences
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            if re.search(r'\b(works by|process|steps|involves)\b', sentence, re.IGNORECASE):
                return sentence.strip()
                
        return ""
        
    def _extract_comparison(self, text: str, question: str) -> str:
        """Extract comparison answer."""
        # Find comparison sentences
        sentences = re.split(r'[.!?]+', text)
        
        comparison_sentences = []
        for sentence in sentences:
            if re.search(r'\b(vs|versus|compared to|difference|while|whereas)\b', sentence, re.IGNORECASE):
                comparison_sentences.append(sentence.strip())
                
        return " ".join(comparison_sentences[:2])  # Return up to 2 sentences
        
    def _extract_causal(self, text: str, question: str) -> str:
        """Extract causal explanation."""
        # Find causal sentences
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            if re.search(r'\b(causes|leads to|results in|because|due to)\b', sentence, re.IGNORECASE):
                return sentence.strip()
                
        return ""
        
    def _extract_generic(self, text: str, question: str) -> str:
        """Extract generic answer."""
        # Return most relevant sentence
        sentences = re.split(r'[.!?]+', text)
        
        if sentences:
            # Return first substantial sentence
            for sentence in sentences:
                if len(sentence.strip()) > 20:
                    return sentence.strip()
                    
        return ""


# Example usage
if __name__ == "__main__":
    print("Testing Smart Question Generator...")
    print("=" * 60)
    
    sample_text = """
    Machine learning is a subset of artificial intelligence that enables 
    systems to learn from data. Neural networks work by processing information 
    through layers of interconnected nodes. The difference between supervised 
    and unsupervised learning is that supervised learning uses labeled data.
    Overfitting causes poor performance on new data because the model 
    memorizes the training set.
    """
    
    generator = SmartQuestionGenerator()
    
    # Analyze text context
    analysis = generator.analyze_text_context(sample_text)
    print(f"Context Analysis:")
    print(f"  Total sentences: {analysis['total_sentences']}")
    print(f"  Has definitions: {analysis['has_definitions']}")
    print(f"  Recommended types: {', '.join(analysis['recommended_types'])}")
    print()
    
    # Generate questions
    questions = generator.generate_questions(sample_text, max_questions=5)
    
    print(f"Generated {len(questions)} questions:\n")
    
    for i, q in enumerate(questions, 1):
        print(f"Question {i} ({q['question_type']}, {q['difficulty']}):")
        print(f"  Q: {q['question']}")
        print(f"  A: {q['answer']}")
        print()
        
    # Test answer extraction
    print("Testing Context-Aware Answer Extraction...")
    print("=" * 60)
    
    extractor = ContextAwareAnswerExtractor()
    
    test_question = "What is machine learning?"
    answer = extractor.extract_answer(sample_text, test_question, "definition")
    
    print(f"Question: {test_question}")
    print(f"Extracted Answer: {answer}")
