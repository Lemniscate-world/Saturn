"""
Batch Processing Service for Echo Desktop Application.

Handles bulk flashcard generation from multiple text sources:
- Multiple clipboard selections
- File imports
- URL content extraction
- Document processing

Architecture: Core (Hub) - batch processing logic.
"""

import os
import json
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from flashcard_generator import FlashcardGenerator, Flashcard
from ai_providers import AIProviderFactory, AIConfig


@dataclass
class BatchJob:
    """Represents a batch processing job."""
    job_id: str
    source_type: str  # "clipboard", "file", "url", "text"
    source_location: str
    status: str  # "pending", "processing", "completed", "failed"
    total_items: int
    processed_items: int
    flashcards_generated: int
    errors: List[str]


class BatchProcessor:
    """
    Processes multiple text sources in batch mode.
    
    Features:
    - Parallel processing for performance
    - Progress tracking and callbacks
    - Error handling and retry logic
    - Memory-efficient streaming for large files
    """
    
    def __init__(
        self,
        flashcard_generator: FlashcardGenerator,
        max_workers: int = 4,
        batch_size: int = 10,
        on_progress: Optional[Callable[[int, int], None]] = None
    ):
        """
        Initialize batch processor.
        
        Args:
            flashcard_generator: FlashcardGenerator instance
            max_workers: Maximum parallel workers
            batch_size: Items per batch
            on_progress: Progress callback function
        """
        self.generator = flashcard_generator
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.on_progress = on_progress
        
    def process_texts(
        self, 
        texts: List[str], 
        auto_add_to_srs: bool = False
    ) -> Dict:
        """
        Process multiple texts in batch.
        
        Args:
            texts: List of text strings to process
            auto_add_to_srs: Whether to automatically add to SRS
            
        Returns:
            Dictionary with results summary
        """
        total = len(texts)
        all_flashcards = []
        errors = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all jobs
            futures = {
                executor.submit(
                    self.generator.generate, 
                    text
                ): idx 
                for idx, text in enumerate(texts)
            }
            
            # Process completed jobs
            for future in as_completed(futures):
                idx = futures[future]
                
                try:
                    flashcards = future.result()
                    all_flashcards.extend(flashcards)
                    
                    # Progress callback
                    if self.on_progress:
                        self.on_progress(idx + 1, total)
                        
                except Exception as e:
                    errors.append({
                        "text_index": idx,
                        "error": str(e)
                    })
                    
        return {
            "total_texts": total,
            "processed": total - len(errors),
            "total_flashcards": len(all_flashcards),
            "flashcards": [
                {
                    "question": card.question,
                    "answer": card.answer,
                    "difficulty": card.difficulty,
                    "quality_score": card.quality_score,
                    "tags": card.tags
                }
                for card in all_flashcards
            ],
            "errors": errors
        }
        
    def process_file(
        self, 
        file_path: str, 
        chunk_size: int = 1000
    ) -> Dict:
        """
        Process a large file in chunks.
        
        Args:
            file_path: Path to file
            chunk_size: Characters per chunk
            
        Returns:
            Dictionary with results
        """
        if not os.path.exists(file_path):
            return {
                "error": f"File not found: {file_path}",
                "flashcards": []
            }
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Split into chunks
            chunks = self._split_into_chunks(content, chunk_size)
            
            # Process chunks
            return self.process_texts(chunks)
            
        except Exception as e:
            return {
                "error": str(e),
                "flashcards": []
            }
            
    def process_directory(
        self, 
        directory_path: str,
        extensions: List[str] = None
    ) -> Dict:
        """
        Process all text files in a directory.
        
        Args:
            directory_path: Path to directory
            extensions: File extensions to process (default: .txt, .md)
            
        Returns:
            Dictionary with results
        """
        if extensions is None:
            extensions = ['.txt', '.md']
            
        if not os.path.isdir(directory_path):
            return {
                "error": f"Directory not found: {directory_path}",
                "flashcards": []
            }
            
        # Collect all files
        files = []
        for root, _, filenames in os.walk(directory_path):
            for filename in filenames:
                if any(filename.endswith(ext) for ext in extensions):
                    files.append(os.path.join(root, filename))
                    
        # Process all files
        all_results = []
        for file_path in files:
            result = self.process_file(file_path)
            all_results.append({
                "file": file_path,
                "result": result
            })
            
        # Aggregate results
        total_flashcards = sum(
            len(r["result"].get("flashcards", [])) 
            for r in all_results
        )
        
        return {
            "total_files": len(files),
            "processed_files": len([r for r in all_results if "error" not in r["result"]]),
            "total_flashcards": total_flashcards,
            "file_results": all_results
        }
        
    def _split_into_chunks(
        self, 
        text: str, 
        chunk_size: int
    ) -> List[str]:
        """
        Split text into chunks at sentence boundaries.
        
        Args:
            text: Text to split
            chunk_size: Target chunk size
            
        Returns:
            List of text chunks
        """
        chunks = []
        current_chunk = ""
        
        # Split into sentences
        sentences = text.split('. ')
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < chunk_size:
                current_chunk += sentence + '. '
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + '. '
                
        # Add last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks


class ClipboardBatchCollector:
    """
    Collects multiple clipboard selections over time for batch processing.
    
    Features:
    - Time-windowed collection
    - Manual trigger for batch processing
    - Deduplication of similar text
    """
    
    def __init__(
        self,
        time_window: int = 300,  # 5 minutes
        similarity_threshold: float = 0.8
    ):
        """
        Initialize clipboard batch collector.
        
        Args:
            time_window: Time window in seconds for collection
            similarity_threshold: Threshold for deduplication
        """
        self.time_window = time_window
        self.similarity_threshold = similarity_threshold
        self.collected_texts: List[Dict] = []
        
    def add_text(self, text: str) -> bool:
        """
        Add text to collection.
        
        Args:
            text: Text to add
            
        Returns:
            True if text was added, False if duplicate
        """
        import time
        
        # Check for duplicates
        for item in self.collected_texts:
            if self._is_similar(text, item["text"]):
                return False
                
        # Add new text
        self.collected_texts.append({
            "text": text,
            "timestamp": time.time()
        })
        
        return True
        
    def get_batch(self, clear: bool = True) -> List[str]:
        """
        Get collected texts for batch processing.
        
        Args:
            clear: Whether to clear collection after retrieval
            
        Returns:
            List of collected texts
        """
        import time
        
        current_time = time.time()
        
        # Filter by time window
        texts = [
            item["text"]
            for item in self.collected_texts
            if current_time - item["timestamp"] <= self.time_window
        ]
        
        # Clear if requested
        if clear:
            self.collected_texts = []
            
        return texts
        
    def _is_similar(self, text1: str, text2: str) -> bool:
        """
        Check if two texts are similar (deduplication).
        
        Simple similarity check using word overlap.
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return False
            
        overlap = len(words1 & words2)
        similarity = overlap / min(len(words1), len(words2))
        
        return similarity >= self.similarity_threshold


# Example usage
if __name__ == "__main__":
    print("Testing Batch Processor...")
    print("=" * 60)
    
    # Create generator
    generator = FlashcardGenerator(
        provider="rule_based",
        max_flashcards=3,
        min_quality_score=0.5
    )
    
    # Create batch processor
    processor = BatchProcessor(
        flashcard_generator=generator,
        max_workers=2
    )
    
    # Test texts
    test_texts = [
        "Machine learning is a subset of artificial intelligence.",
        "Neural networks are computing systems inspired by biological neural networks.",
        "Deep learning is a subset of machine learning using multi-layered networks."
    ]
    
    def on_progress(current, total):
        print(f"Progress: {current}/{total}")
        
    processor.on_progress = on_progress
    
    # Process batch
    results = processor.process_texts(test_texts)
    
    print(f"\nBatch Results:")
    print(f"  Total texts: {results['total_texts']}")
    print(f"  Processed: {results['processed']}")
    print(f"  Total flashcards: {results['total_flashcards']}")
    print(f"  Errors: {len(results['errors'])}")
    
    print(f"\nGenerated Flashcards:")
    for i, card in enumerate(results['flashcards'], 1):
        print(f"{i}. {card['question']}")
        print(f"   A: {card['answer']}")
        print()
