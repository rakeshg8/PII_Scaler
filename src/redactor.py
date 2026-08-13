import re
import logging
from src.recognizers import (
    recognize_email, recognize_phone, recognize_ssn, recognize_credit_card,
    recognize_ip_address, recognize_date_of_birth, recognize_address,
    make_person_recognizer, make_company_recognizer
)
from src.registry import RecognizerRegistry
from src.pseudonymizer import EntityMapper
from src.docx_io import iter_paragraphs, redact_paragraph

def build_promoter_seeds(paragraphs):
    """
    Extracts promoter names and organizations from the document to seed the recognizer.
    """
    promoter_names = set()
    promoter_orgs = set()
    
    for i, p in enumerate(paragraphs):
        text = p.text.strip()
        target_text = None
        # Anchor 1: exact paragraph text or header separated by newline
        if "Our Promoters" in text:
            if text == "Our Promoters" and i + 1 < len(paragraphs):
                target_text = paragraphs[i + 1].text.strip()
            elif text.startswith("Our Promoters\n") or text.startswith("Our Promoters\r\n"):
                parts = text.split("\n", 1)
                target_text = parts[1].strip()
        # Anchor 2: containing Individual Promoters
        elif "Individual Promoters" in text:
            idx = text.find("Individual Promoters")
            target_text = text[idx + len("Individual Promoters"):]
            if "." in target_text:
                target_text = target_text.split(".")[0]
        
        if target_text:
            normalized = re.sub(r"\b(?:and|&)\b", ",", target_text)
            items = [item.strip() for item in normalized.split(",")]
            for item in items:
                # Clean trailing explanations or verbs
                item = re.sub(r"\s+are\s+.*$", "", item, flags=re.IGNORECASE)
                item = re.sub(r"\s+For\s+further\s+.*$", "", item, flags=re.IGNORECASE)
                item = item.strip()
                
                # Check for capitalized names
                if item and item[0].isupper() and len(item.split()) > 1:
                    if any(w in item.lower() for w in ["page", "chapter", "section", "management", "personnel", "director", "promoter", "company", "secretary", "officer", "statutory", "auditor"]):
                        continue
                    if any(suffix in item for suffix in ["Limited", "Ltd", "LLP", "Inc", "Trust", "Corporation", "Corp", "Industries", "Private"]):
                        promoter_orgs.add(item)
                    else:
                        promoter_names.add(item)
                        # Generate Surname, Given Names inverted variant
                        parts = item.split()
                        if len(parts) > 1:
                            surname = parts[-1]
                            given_names = " ".join(parts[:-1])
                            inverted = f"{surname}, {given_names}"
                            promoter_names.add(inverted)
                        
    logging.info(f"Extracted promoter seeds: Names: {len(promoter_names)}, Orgs: {len(promoter_orgs)}")
    return promoter_names, promoter_orgs

class Redactor:
    def __init__(self):
        self.registry = RecognizerRegistry()
        self.mapper = EntityMapper()

    def setup_recognizers(self, paragraphs):
        # 1. Build promoter seeds
        seed_names, seed_orgs = build_promoter_seeds(paragraphs)
        
        # 2. Register base recognizers
        self.registry.register(recognize_email)
        self.registry.register(recognize_phone)
        self.registry.register(recognize_ssn)
        self.registry.register(recognize_credit_card)
        self.registry.register(recognize_ip_address)
        self.registry.register(recognize_date_of_birth)
        self.registry.register(recognize_address)
        
        # 3. Register PERSON and COMPANY recognizers with seeds
        self.registry.register(make_person_recognizer(seed_names))
        self.registry.register(make_company_recognizer(seed_orgs))

    def redact_document(self, doc):
        paragraphs = list(iter_paragraphs(doc))
        self.setup_recognizers(paragraphs)
        
        all_redactions = []
        for p in paragraphs:
            text = p.text
            if not text.strip():
                continue
            
            # Detect
            spans = self.registry.get_all_spans(text)
            # Merge
            merged_spans = self.registry.merge_spans(spans)
            # Replace
            redactions = redact_paragraph(p, merged_spans, self.mapper)
            all_redactions.extend(redactions)
            
        return all_redactions
