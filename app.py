from fastapi import FastAPI
from datetime import date
from models import MemoryItem, Feedback
from engine import review
from db import connect, init_db
from graph import compute_centrality
from flashcard_generator import FlashcardGenerator, Flashcard
from clipboard_monitor import ClipboardMonitor, ClipboardEvent
from batch_processor import BatchProcessor
from typing import List
import uuid

app = FastAPI(title="Echo Memory Engine", version="0.2.0")

conn = connect()
init_db(conn)

# Initialize flashcard generator (uses OPENAI_API_KEY env var if available)
flashcard_gen = FlashcardGenerator(max_flashcards=5, min_quality_score=0.6)


@app.get("/health")
def health():
    return {"status": "alive", "version": "Echo v0.2.0", "features": ["srs", "clipboard", "ai_generation"]}


@app.post("/memory")
def upsert_memory(payload: dict):
    cur = conn.cursor()

    # Insert or update the item (for update, we need to handle centrality recompute)
    cur.execute("""
    INSERT OR REPLACE INTO memory_items (
        id, source, note_path, block_ref,
        interval, ease, confidence, repetitions, centrality,
        last_review, next_review, created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        payload["id"],
        payload["source"],
        payload["note_path"],
        payload.get("block_ref"),
        1.0,
        2.5,
        0.5,
        0,
        0.0,  # initial centrality
        None,  # last_review
        date.today(),  # next_review
        date.today()  # created_at
    ))

    # Recompute centrality for all items
    cur.execute("SELECT id, source, note_path FROM memory_items")
    all_items = [{"id": row[0], "source": row[1], "note_path": row[2]} for row in cur.fetchall()]
    centrality_scores = compute_centrality(all_items)
    
    # Update centrality for all
    for item_id, score in centrality_scores.items():
        cur.execute("UPDATE memory_items SET centrality = ? WHERE id = ?", (score, item_id))

    conn.commit()
    return {"status": "ok"}


@app.get("/reviews/today")
def reviews_today():
    cur = conn.cursor()
    today = date.today()
    
    cur.execute("""
    SELECT id, source, note_path, block_ref, interval, ease, confidence, repetitions, centrality, last_review, next_review
    FROM memory_items
    WHERE next_review <= ?
    ORDER BY centrality DESC, next_review ASC
    """, (today,))
    
    rows = cur.fetchall()
    reviews = []
    for row in rows:
        reviews.append({
            "id": row[0],
            "source": row[1],
            "note_path": row[2],
            "block_ref": row[3],
            "interval": row[4],
            "ease": row[5],
            "confidence": row[6],
            "repetitions": row[7],
            "centrality": row[8],
            "last_review": row[9],
            "next_review": row[10]
        })
    
    return reviews


@app.post("/review")
def submit_review(payload: dict):
    item_id = payload["id"]
    feedback = Feedback(payload["feedback"])
    today = date.today()
    
    cur = conn.cursor()
    
    # Fetch current item
    cur.execute("""
    SELECT id, source, note_path, block_ref, interval, ease, confidence, repetitions, last_review, next_review
    FROM memory_items
    WHERE id = ?
    """, (item_id,))
    
    row = cur.fetchone()
    if not row:
        return {"error": "Memory item not found"}
    
    # Reconstruct MemoryItem
    item = MemoryItem(
        id=row[0],
        source=row[1],
        note_path=row[2],
        block_ref=row[3],
        interval=row[4],
        ease=row[5],
        confidence=row[6],
        repetitions=row[7],
        last_review=row[8] if row[8] else None,
        next_review=row[9]
    )
    
    # Apply review
    updated_item = review(item, feedback, today)
    
    # Update item in DB
    cur.execute("""
    UPDATE memory_items
    SET interval = ?, ease = ?, confidence = ?, repetitions = ?, last_review = ?, next_review = ?
    WHERE id = ?
    """, (
        updated_item.interval,
        updated_item.ease,
        updated_item.confidence,
        updated_item.repetitions,
        updated_item.last_review,
        updated_item.next_review,
        item_id
    ))
    
    # Insert into review_history
    cur.execute("""
    INSERT INTO review_history (memory_id, review_date, feedback, interval_after, ease_after, confidence_after)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        item_id,
        today,
        feedback.value,
        updated_item.interval,
        updated_item.ease,
        updated_item.confidence
    ))
    
    conn.commit()
    return {"status": "ok", "next_review": updated_item.next_review.isoformat()}


@app.post("/generate-flashcards")
def generate_flashcards(payload: dict):
    """
    Generate flashcards from text using AI.
    
    Args:
        text: Source text to generate flashcards from
        auto_add: If True, automatically add flashcards to SRS system
    
    Returns:
        List of generated flashcards with quality scores
    """
    text = payload.get("text", "")
    auto_add = payload.get("auto_add", False)
    
    if len(text) < 10:
        return {"error": "Text too short (minimum 10 characters)"}
    
    # Generate flashcards
    flashcards = flashcard_gen.generate(text)
    
    # Auto-add to SRS if requested
    if auto_add:
        added_ids = []
        for card in flashcards:
            card_id = str(uuid.uuid4())
            
            # Add to memory_items table
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO memory_items (
                id, source, note_path, block_ref,
                interval, ease, confidence, repetitions, centrality,
                last_review, next_review, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                card_id,
                f"Q: {card.question}\nA: {card.answer}",
                "flashcard",
                None,
                1.0,
                2.5,
                0.5,
                0,
                0.0,
                None,
                date.today(),
                date.today()
            ))
            added_ids.append(card_id)
            
        conn.commit()
        
        return {
            "flashcards": [
                {
                    "question": card.question,
                    "answer": card.answer,
                    "difficulty": card.difficulty,
                    "quality_score": card.quality_score,
                    "tags": card.tags
                }
                for card in flashcards
            ],
            "added_to_srs": True,
            "card_ids": added_ids
        }
    
    
    return {
        "flashcards": [
            {
                "question": card.question,
                "answer": card.answer,
                "difficulty": card.difficulty,
                "quality_score": card.quality_score,
                "tags": card.tags
            }
            for card in flashcards
        ],
        "added_to_srs": False
    }


@app.post("/capture-clipboard")
def capture_clipboard():
    """
    Manually capture current clipboard content and generate flashcards.
    
    Returns:
        Captured text and generated flashcards
    """
    monitor = ClipboardMonitor(min_text_length=10)
    event = monitor.capture_now()
    
    if not event:
        return {"error": "No text in clipboard or text too short"}
    
    # Generate flashcards from captured text
    flashcards = flashcard_gen.generate(event.text)
    
    return {
        "captured_text": event.text,
        "timestamp": event.timestamp,
        "flashcards": [
            {
                "question": card.question,
                "answer": card.answer,
                "difficulty": card.difficulty,
                "quality_score": card.quality_score
            }
            for card in flashcards
        ]
    }


@app.post("/batch-generate")
def batch_generate_flashcards(payload: dict):
    """
    Generate flashcards from multiple texts in batch.
    
    Args:
        texts: List of text strings to process
        auto_add: If True, automatically add all flashcards to SRS
        
    Returns:
        Batch processing results with all generated flashcards
    """
    texts = payload.get("texts", [])
    auto_add = payload.get("auto_add", False)
    
    if not texts:
        return {"error": "No texts provided"}
    
    if len(texts) > 100:
        return {"error": "Maximum 100 texts per batch"}
    
    # Create batch processor
    processor = BatchProcessor(
        flashcard_generator=flashcard_gen,
        max_workers=4
    )
    
    # Process batch
    results = processor.process_texts(texts, auto_add_to_srs=auto_add)
    
    # Auto-add to SRS if requested
    if auto_add and results["flashcards"]:
        added_ids = []
        cur = conn.cursor()
        
        for card in results["flashcards"]:
            card_id = str(uuid.uuid4())
            
            cur.execute("""
            INSERT INTO memory_items (
                id, source, note_path, block_ref,
                interval, ease, confidence, repetitions, centrality,
                last_review, next_review, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                card_id,
                f"Q: {card['question']}\nA: {card['answer']}",
                "batch_flashcard",
                None,
                1.0,
                2.5,
                0.5,
                0,
                0.0,
                None,
                date.today(),
                date.today()
            ))
            added_ids.append(card_id)
            
        conn.commit()
        results["added_to_srs"] = True
        results["card_ids"] = added_ids
    
    return results


@app.post("/process-file")
def process_file(payload: dict):
    """
    Process a file and generate flashcards from its content.
    
    Args:
        file_path: Path to file to process
        chunk_size: Characters per chunk (default: 1000)
        
    Returns:
        Processing results with generated flashcards
    """
    file_path = payload.get("file_path", "")
    chunk_size = payload.get("chunk_size", 1000)
    
    if not file_path:
        return {"error": "No file path provided"}
    
    # Create batch processor
    processor = BatchProcessor(
        flashcard_generator=flashcard_gen,
        max_workers=2
    )
    
    # Process file
    results = processor.process_file(file_path, chunk_size)
    
    return results
