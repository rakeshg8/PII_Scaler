import re
import spacy

# Constants
INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat",
    "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
    "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
    "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir",
    "Ladakh", "Lakshadweep", "Puducherry"
]

EXEMPT_COMPANIES = {
    "ksh international limited",
    "ksh international",
    "the company",
    "the issuer"
}

# Pre-compile Regex Patterns

# EMAIL
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# PHONE
PHONE_TIER1_REGEX = re.compile(r"\+\s?91[-\s]?\d{5}[-\s]?\d{5}|\+\s?91[-\s]?\d{10}")
PHONE_LANDLINE_REGEX = re.compile(r"\+\s?91[-\s]?\d{2,4}[-\s]?\d{6,8}|\b\+?\d{2,4}[-\s]?\d{6,8}\b")
PHONE_TIER2_REGEX = re.compile(r"\b\d{10}\b")
PHONE_CONTEXT_REGEX = re.compile(r"(?:Tel|Telephone|Phone|Mobile|Fax|Contact)", re.IGNORECASE)

# SSN
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# CREDIT CARD
CC_REGEX = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

# IP ADDRESS
IPV4_REGEX = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")
IPV6_REGEX = re.compile(r"\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b")

# DATE OF BIRTH
DOB_MONTHS = r"(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
DOB_PATTERN_NUMERIC = re.compile(r"\b\d{1,2}[-/ ](?:[A-Za-z]+|\d{1,2})[-/ ]\d{2,4}\b")
DOB_PATTERN_MDY = re.compile(rf"\b{DOB_MONTHS}\s+\d{{1,2}},\s+\d{{4}}\b", re.IGNORECASE)
DOB_PATTERN_DMY = re.compile(rf"\b\d{{1,2}}\s+{DOB_MONTHS}\s+\d{{4}}\b", re.IGNORECASE)
DOB_CONTEXT_REGEX = re.compile(r"(?:date of birth|DOB|born on|age as on)", re.IGNORECASE)

# ADDRESS
PIN_REGEX = re.compile(r"\b\d{3}[\s-]?\d{3}\b")

# COMPANY Suffix booster
COMPANY_SUFFIX_REGEX = re.compile(r"\b[A-Z][\w&.,' -]+?(?:Private\s+|Pvt\.?\s+)?(?:Limited|Ltd\.?|LLP|Inc\.?|& Co\.?|Corporation|Corp\.?|Trust|Bank|Industries)\b")

# Global spacy cache
_nlp = None

def get_spacy_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except Exception:
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], capture_output=True)
            _nlp = spacy.load("en_core_web_sm")
    return _nlp

# Luhn check
def luhn_check(card_number: str) -> bool:
    digits = [int(d) for d in card_number if d.isdigit()]
    if not (13 <= len(digits) <= 19):
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0

# EMAIL
def recognize_email(text: str):
    for match in EMAIL_REGEX.finditer(text):
        yield (match.start(), match.end(), "EMAIL", match.group(0), 0.95)

# PHONE
def recognize_phone(text: str):
    # Tier 1 +91 (no context needed)
    for match in PHONE_TIER1_REGEX.finditer(text):
        yield (match.start(), match.end(), "PHONE", match.group(0), 0.95)
    
    # Build list of valid context spans by finding all triggers
    context_spans = []
    for m in PHONE_CONTEXT_REGEX.finditer(text):
        start_span = m.end()
        # Find next boundary in text[start_span:]
        rest_text = text[start_span:]
        boundary_pattern = re.compile(
            r"\n|(?:\.\s+)|\b(?:Tel|Telephone|Phone|Mobile|Fax|Contact)\b",
            re.IGNORECASE
        )
        bound_match = boundary_pattern.search(rest_text)
        if bound_match:
            end_span = start_span + bound_match.start()
        else:
            end_span = len(text)
        context_spans.append((start_span, end_span))

    def is_in_context(pos):
        # Check forward list context
        for cs, ce in context_spans:
            if cs <= pos <= ce:
                return True
        # Check standard 25-character backward lookback
        window = text[max(0, pos - 25):pos]
        if PHONE_CONTEXT_REGEX.search(window):
            return True
        return False

    # Tier 1 Landline (requires context)
    for match in PHONE_LANDLINE_REGEX.finditer(text):
        val = match.group(0)
        # Skip bare 10-digit numbers matching landline regex (handled by Tier 2)
        if val.isdigit() and len(val) == 10:
            continue
        if is_in_context(match.start()):
            yield (match.start(), match.end(), "PHONE", val, 0.85)

    # Tier 2 Bare 10-digit (requires context)
    for match in PHONE_TIER2_REGEX.finditer(text):
        if is_in_context(match.start()):
            yield (match.start(), match.end(), "PHONE", match.group(0), 0.80)

# SSN
def recognize_ssn(text: str):
    for match in SSN_REGEX.finditer(text):
        yield (match.start(), match.end(), "SSN", match.group(0), 1.0)

# CREDIT CARD
def recognize_credit_card(text: str):
    for match in CC_REGEX.finditer(text):
        matched_val = match.group(0)
        if luhn_check(matched_val):
            yield (match.start(), match.end(), "CREDIT_CARD", matched_val, 0.95)

# IP ADDRESS
def recognize_ip_address(text: str):
    for match in IPV4_REGEX.finditer(text):
        yield (match.start(), match.end(), "IP_ADDRESS", match.group(0), 0.95)
    for match in IPV6_REGEX.finditer(text):
        yield (match.start(), match.end(), "IP_ADDRESS", match.group(0), 0.95)

# DATE OF BIRTH
def recognize_date_of_birth(text: str):
    patterns = [DOB_PATTERN_NUMERIC, DOB_PATTERN_MDY, DOB_PATTERN_DMY]
    for pattern in patterns:
        for match in pattern.finditer(text):
            start = match.start()
            window = text[max(0, start - 45):start]
            if DOB_CONTEXT_REGEX.search(window):
                yield (match.start(), match.end(), "DATE_OF_BIRTH", match.group(0), 0.90)

# PERSON
HEADING_STOPLIST = {
    "SECTION", "TABLE OF CONTENTS", "DEFINITIONS AND ABBREVIATIONS", "RISK FACTORS",
    "INTRODUCTION", "THE ISSUE", "GENERAL INFORMATION", "CAPITAL STRUCTURE",
    "OBJECTS OF THE ISSUE", "BASIS FOR ISSUE PRICE", "STATEMENT OF TAX BENEFITS",
    "SECTION II", "SECTION III", "SECTION IV", "SECTION V", "SECTION VI", "SECTION VII",
    "INDUSTRY OVERVIEW", "OUR BUSINESS", "REGULATIONS AND POLICIES", "HISTORY AND CERTAIN CORPORATE MATTERS",
    "OUR MANAGEMENT", "OUR PROMOTERS AND PROMOTER GROUP", "OUR GROUP COMPANIES",
    "RELATED PARTY TRANSACTIONS", "DIVIDEND POLICY", "SECTION VIII", "FINANCIAL INFORMATION",
    "MANAGEMENT’S DISCUSSION AND ANALYSIS", "OUTSTANDING LITIGATION AND MATERIAL DEVELOPMENTS",
    "GOVERNMENT AND OTHER APPROVALS", "OTHER REGULATORY AND STATUTORY DISCLOSURES",
    "SECTION IX", "OFFERING INFORMATION", "TERMS OF THE ISSUE", "ISSUE STRUCTURE",
    "ISSUE PROCEDURE", "RESTRICTIONS ON FOREIGN OWNERSHIP", "SECTION X", "MAIN PROVISIONS OF ARTICLES OF ASSOCIATION",
    "SECTION XI", "OTHER INFORMATION", "MATERIAL CONTRACTS AND DOCUMENTS AND INSPECTION",
    "DECLARATION", "OUR PROMOTERS", "PROMOTER GROUP", "GROUP COMPANIES"
}

NER_STOPLIST = {
    "DOB", "SSN", "IP", "IPV6", "IPV4", "ID", "TEL", "FAX", "EMAIL", "PHONE",
    "MOBILE", "CONTACT", "REGISTRAR", "ISSUER", "COMPANY", "CREDIT CARD",
    "CHAIRMAN", "DIRECTOR", "PROMOTER", "PROMOTERS", "MANAGEMENT", "BOARD",
    "AUDITOR", "AUDITORS", "BANK", "BANKER", "BANKERS", "YEAR", "YEARS", "AGE"
}

def is_stopword(text: str) -> bool:
    cleaned = text.strip().upper()
    if cleaned in NER_STOPLIST:
        return True
    if len(cleaned) <= 2:
        return True
    return False

def is_heading(name_text: str) -> bool:
    cleaned = name_text.strip().upper()
    if cleaned in HEADING_STOPLIST:
        return True
    if name_text.isupper() and any(k in cleaned for k in ["SECTION", "TABLE", "CONTENTS", "DEFINITIONS", "RISK", "PROMOTERS", "MANAGEMENT", "FINANCIAL", "STATEMENTS"]):
        return True
    return False

def make_person_recognizer(seed_names):
    def recognize_person(text: str):
        # 1. Exact seed-list matching
        for seed in seed_names:
            if not seed or len(seed.strip()) < 3:
                continue
            pattern = re.compile(rf"\b{re.escape(seed)}\b", re.IGNORECASE)
            for match in pattern.finditer(text):
                start = match.start()
                # If seed has a comma (inverted variant), prevent matching across list boundaries
                if "," in seed:
                    prefix = text[max(0, start - 15):start].strip()
                    if prefix:
                        words = prefix.split()
                        if words:
                            last_word = words[-1].strip(".,:;\"'()")
                            if last_word and last_word[0].isupper():
                                if last_word.lower() not in ["mr", "mrs", "ms", "dr", "shri", "smt", "km"]:
                                    continue
                yield (match.start(), match.end(), "PERSON", match.group(0), 0.99)

        # 2. spaCy NER matching
        nlp = get_spacy_nlp()
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                matched_text = ent.text.strip()
                if len(matched_text.split()) < 2:
                    continue
                if is_heading(matched_text) or is_stopword(matched_text):
                    continue
                # Skip if it contains typical company suffixes
                if any(suffix in matched_text for suffix in ["Limited", "Ltd", "LLP", "Inc", "Trust", "Corporation", "Corp", "Industries", "Private"]):
                    continue
                yield (ent.start_char, ent.end_char, "PERSON", ent.text, 0.70)
    return recognize_person

# COMPANY
def make_company_recognizer(seed_orgs):
    def recognize_company(text: str):
        # 1. Exact seed-list matching
        for seed in seed_orgs:
            if not seed or len(seed.strip()) < 3:
                continue
            pattern = re.compile(rf"\b{re.escape(seed)}\b", re.IGNORECASE)
            for match in pattern.finditer(text):
                matched_val = match.group(0)
                if matched_val.strip().lower() not in EXEMPT_COMPANIES:
                    yield (match.start(), match.end(), "COMPANY", matched_val, 0.99)

        # 2. Suffix regex matching
        for match in COMPANY_SUFFIX_REGEX.finditer(text):
            matched_val = match.group(0)
            if matched_val.strip().lower() not in EXEMPT_COMPANIES and not is_stopword(matched_val):
                yield (match.start(), match.end(), "COMPANY", matched_val, 0.85)

        # 3. spaCy ORG matching
        nlp = get_spacy_nlp()
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ == "ORG":
                matched_text = ent.text.strip()
                if matched_text.lower() in EXEMPT_COMPANIES or is_stopword(matched_text):
                    continue
                if not any(c.isalpha() for c in matched_text):
                    continue
                
                # Check for generic roles/bodies stoplist
                new_cleaned = matched_text.lower()
                if new_cleaned in [
                    "board of directors", "statutory auditors", "audit committee", 
                    "registrar of companies", "statutory auditor", "board", "committee",
                    "management", "promoters", "promoter", "company", "issuer", 
                    "directors", "director", "sub-committee", "restated financial statements",
                    "financial statements", "equity shares", "shares", "board of director"
                ]:
                    continue
                
                # Check for NER over-extension: length > 60 chars
                if len(matched_text) > 60:
                    suffix_match = COMPANY_SUFFIX_REGEX.search(matched_text)
                    if suffix_match:
                        new_start = ent.start_char + suffix_match.start()
                        new_end = ent.start_char + suffix_match.end()
                        new_text = suffix_match.group(0)
                        new_cleaned = new_text.strip().lower()
                        if new_cleaned not in EXEMPT_COMPANIES and not is_stopword(new_text):
                            if new_cleaned not in [
                                "board of directors", "statutory auditors", "audit committee", 
                                "registrar of companies", "statutory auditor", "board", "committee",
                                "management", "promoters", "promoter", "company", "issuer", 
                                "directors", "director", "sub-committee", "restated financial statements",
                                "financial statements", "equity shares", "shares", "board of director"
                            ]:
                                yield (new_start, new_end, "COMPANY", new_text, 0.70)
                    # If no suffix matches, discard the over-long NER match entirely
                else:
                    yield (ent.start_char, ent.end_char, "COMPANY", ent.text, 0.65)
    return recognize_company

# ADDRESS
def recognize_address(text: str):
    for match in PIN_REGEX.finditer(text):
        pin_end = match.end()
        pin_start = match.start()
        
        start_idx = max(0, pin_start - 200)
        window = text[start_idx:pin_start]
        
        # 1. First look for "Address:" anchor
        addr_match = list(re.finditer(r"\bAddress\s*:\s*", window, re.IGNORECASE))
        if addr_match:
            actual_start = start_idx + addr_match[-1].end()
        else:
            # 2. Check for common address starting keywords
            addr_start_regex = re.compile(
                r"\b(?:Flat|Plot|Shop|Building|Bunglow|Apartment|Suite|Unit|No\.?|S\.\s*no\.?|Plot\s+no\.?|Tower|Level|Floor|Block|Phase|S\.\s*No|Village|Plot\s+No|S\s+no|Flat\s+–\s*\d+|Campus|Park|Centre|House|Plaza|Estate|Road|Marg|Street|Lane|Society|Chamber|Chambers)\b|\b[A-Z]-\d{1,4}\b",
                re.IGNORECASE
            )
            start_matches = list(addr_start_regex.finditer(window))
            if start_matches:
                first_match = start_matches[0]
                first_match_pos = first_match.start()
                leading_text = window[:first_match_pos]
                
                # Check for boundaries (newline, colon, tab, or dash) in leading text
                bounds = list(re.finditer(r"(?:[\n\t:]|–\s+|- \s+)\s*", leading_text))
                if bounds:
                    actual_start = start_idx + bounds[-1].end()
                else:
                    # Check for leading number digits (like "12 " or "201, ") before the match
                    num_match = list(re.finditer(r"\b\d{1,5}\b\s*,?\s*$", leading_text))
                    if num_match:
                        actual_start = start_idx + num_match[-1].start()
                    else:
                        actual_start = start_idx + first_match_pos
            else:
                # 3. Fallback to last boundary in window
                bounds = list(re.finditer(r"(?:[\n\t:]|–\s+|- \s+)\s*", window))
                if bounds:
                    actual_start = start_idx + bounds[-1].end()
                else:
                    actual_start = start_idx
            
        # Look forward for the end of the address block (up to 100 chars or boundary/contact label)
        forward_window = text[pin_end:pin_end + 100]
        end_match = re.search(r"(?:[.\n?!](?:\s+|$))|\b(?:Tel|Telephone|Phone|Fax|Email|E-mail|Website|Contact|CIN|SEBI|URL)\b", forward_window, re.IGNORECASE)
        if end_match:
            actual_end = pin_end + end_match.start()
        else:
            actual_end = min(len(text), pin_end + len(forward_window.rstrip()))
            
        address_text = text[actual_start:actual_end].strip()
        
        contains_state_or_india = False
        if "india" in address_text.lower():
            contains_state_or_india = True
        else:
            for state in INDIAN_STATES:
                if state.lower() in address_text.lower():
                    contains_state_or_india = True
                    break
        
        if contains_state_or_india:
            yield (actual_start, actual_end, "ADDRESS", text[actual_start:actual_end], 0.80)
