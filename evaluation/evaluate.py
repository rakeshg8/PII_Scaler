import json
import re
import os
import sys
from src.redactor import Redactor
from src.registry import PRIORITY

class DummyParagraph:
    def __init__(self, text):
        self.text = text

def get_iou(start1, end1, start2, end2):
    intersection = max(0, min(end1, end2) - max(start1, start2))
    union = (end1 - start1) + (end2 - start2) - intersection
    if union == 0:
        return 0
    return intersection / union

def evaluate():
    gold_path = "evaluation/gold_annotations.json"
    if not os.path.exists(gold_path):
        print(f"Error: Gold annotations not found at {gold_path}")
        sys.exit(1)

    with open(gold_path, "r", encoding="utf-8") as f:
        pages = json.load(f)

    # Initialize redactor with all page texts to build seed lists
    dummy_paragraphs = [DummyParagraph(p["text"]) for p in pages]
    redactor = Redactor()
    redactor.setup_recognizers(dummy_paragraphs)

    # Performance tracking per PII type
    pii_types = PRIORITY + ["Overall"]
    stats = {t: {"tp": 0, "fp": 0, "fn": 0} for t in pii_types}

    total_tokens = 0
    correct_tokens = 0

    for page in pages:
        text = page["text"]
        gold_spans = page.get("spans", [])
        
        # Run detection
        detected_spans = redactor.registry.get_all_spans(text)
        merged_spans = redactor.registry.merge_spans(detected_spans)

        # Match spans using IoU > 0.5 and same entity type
        matched_gold_indices = set()
        matched_detected_indices = set()

        for g_idx, g_span in enumerate(gold_spans):
            g_start, g_end, g_type = g_span["start"], g_span["end"], g_span["type"]
            best_iou = 0
            best_d_idx = -1
            
            for d_idx, d_span in enumerate(merged_spans):
                d_start, d_end, d_type, _, _ = d_span
                if d_idx in matched_detected_indices:
                    continue
                if g_type == d_type:
                    iou = get_iou(g_start, g_end, d_start, d_end)
                    if iou > 0.5 and iou > best_iou:
                        best_iou = iou
                        best_d_idx = d_idx
                        
            if best_d_idx != -1:
                matched_gold_indices.add(g_idx)
                matched_detected_indices.add(best_d_idx)
                stats[g_type]["tp"] += 1
                stats["Overall"]["tp"] += 1
            else:
                stats[g_type]["fn"] += 1
                stats["Overall"]["fn"] += 1

        # Count FP (unmatched detected spans)
        for d_idx, d_span in enumerate(merged_spans):
            if d_idx not in matched_detected_indices:
                d_type = d_span[2]
                if d_type in stats:
                    stats[d_type]["fp"] += 1
                stats["Overall"]["fp"] += 1

        # Token-level accuracy
        tokens = list(re.finditer(r"\S+", text))
        for tok in tokens:
            t_start = tok.start()
            t_end = tok.end()
            
            is_gold_pii = any(max(t_start, g["start"]) < min(t_end, g["end"]) for g in gold_spans)
            is_detected_pii = any(max(t_start, d[0]) < min(t_end, d[1]) for d in merged_spans)
            
            total_tokens += 1
            if is_gold_pii == is_detected_pii:
                correct_tokens += 1

    # Print results table
    print(f"{'PII Type':<20} | {'TP':<5} | {'FP':<5} | {'FN':<5} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10}")
    print("-" * 75)
    
    for t in pii_types:
        tp = stats[t]["tp"]
        fp = stats[t]["fp"]
        fn = stats[t]["fn"]
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        print(f"{t:<20} | {tp:<5} | {fp:<5} | {fn:<5} | {precision:.4f}     | {recall:.4f}  | {f1:.4f}")

    token_accuracy = correct_tokens / total_tokens if total_tokens > 0 else 0.0
    print(f"\nToken-level Accuracy: {token_accuracy:.4f} ({correct_tokens}/{total_tokens} tokens)")

if __name__ == "__main__":
    evaluate()
