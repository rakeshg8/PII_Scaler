# PII Redaction Tool

A modular, extensible, and high-precision Python tool to redact and pseudonymize Personally Identifiable Information (PII) inside Microsoft Word documents (`.docx`), specifically optimized for Indian financial and prospectus disclosures (such as Red Herring Prospectuses).

Instead of blacking out text, it substitutes PII with realistic, locale-specific fake alternatives (e.g. replacing a promoter name with a fake Indian name, or a corporate address with a realistic Indian street address and PIN code) while preserving the original document's structure and layout.

---

## Architecture & Approach

This tool implements a **hybrid regex + Named Entity Recognition (NER)** pipeline using a custom **Recognizer-Registry Pattern** inspired by Microsoft Presidio. 

1. **`docx_io`**: Traverser that recursively walks the DOCX document body, table rows, and nested table cells to concatenate text runs, mapping character indexes back to run offsets for replacement.
2. **`recognizers`**: A collection of isolated detection functions (each implementing standard rules, context checks, or spaCy NER pipelines) that return standardized match spans.
3. **`registry`**: Orchestrates detection across all registered recognizers and resolves overlaps using a priority list (`SSN` > `CREDIT_CARD` > `EMAIL` > `PHONE` > `IP_ADDRESS` > `DATE_OF_BIRTH` > `ADDRESS` > `PERSON` > `COMPANY`).
4. **`pseudonymizer`**: Maps original values consistently to realistic fake text using `Faker` (with the `en_IN` locale for Indian entities).
5. **`redactor`**: Coordinates the entire workflow: builds promoter name seeds, executes detection, merges overlaps, and substitutes text right-to-left.

---

## Getting Started

### Installation
Ensure Python 3.10+ is installed, then run:
```bash
pip install -r requirements.txt
```
The dependencies include `python-docx`, `spacy`, `faker`, and `pytest`. The lightweight spaCy model (`en_core_web_sm`) will be automatically downloaded on the first run of the tool.

### Running Redaction
To run the redaction tool on a document:
```bash
python main.py --input data/input/RHP.docx --output data/output/RHP_redacted.docx --report data/output/report.json
```
- `--input`: Path to the input `.docx` file.
- `--output`: Path where the redacted `.docx` will be saved.
- `--report` (optional): Path to save a JSON report of the redactions made (log files contain type and original length only — **never** the original sensitive PII text).

### Running Tests
To run the recognizer unit tests:
```bash
python -m pytest tests/test_recognizers.py
```

### Running Evaluation
To evaluate accuracy, precision, and recall on the gold-annotated dataset:
```bash
python -m evaluation.evaluate
```

---

## Critical Design Decisions & Heuristics

1. **Issuer Company Exemption**: "KSH International Limited", "the Company", and "the Issuer" are explicitly exempted from redact as they are the public subject of disclosure.
2. **Date of Birth Context Gating**: Date-shaped spans are only classified as DOB if trigger terms (e.g. `DOB`, `date of birth`, `born on`, `age as on`) appear within 45 characters preceding the date. This prevents redacting standard prospectus dates or fiscal year endings.
3. **Phone Number Gating**: Tier-2 phone numbers (bare 10-digit numbers) are only redacted if preceded by labels like `Tel`, `Phone`, `Mobile`. This protects corporate IDs or registration numbers from false positives.
4. **Luhn Algorithm Guard**: Candidates for credit cards are validated using the Luhn algorithm. Long registration IDs or numerical strings that do not pass the checksum are ignored.
5. **Promoter Seed List Booster**: The redactor automatically scans the `"Our Promoters"` section when starting. It extracts promoter names to seed an exact-match recognizer, bypassing spaCy NER limitations across 120+ pages.
6. **Formatting Tradeoff**: When writing replacements, all runs touched by a span are collapsed into the first run (`run[0]`), inheriting its formatting. This loses intra-paragraph fine-grained styling (like a single bolded word mid-sentence) but guarantees textual correctness. Paragraphs with no PII are completely untouched, preserving their formatting.

---

## How to Extend the Tool to a New PII Type

The tool is designed for plug-and-play extensions. To add a new PII type:
1. **Implement a Recognizer**: Create a detector function in [src/recognizers.py](file:///c:/Users/yramu/Desktop/PII_Scaler/src/recognizers.py):
   ```python
   def recognize_new_pii(text: str):
       # Yield (start, end, "NEW_PII_TYPE", matched_text, confidence)
       pass
   ```
2. **Register it in registry**: Register the recognizer in [src/registry.py](file:///c:/Users/yramu/Desktop/PII_Scaler/src/registry.py) by adding `"NEW_PII_TYPE"` to the `PRIORITY` list at your desired precedence level.
3. **Register it in redactor**: Add registration in [src/redactor.py](file:///c:/Users/yramu/Desktop/PII_Scaler/src/redactor.py) under `setup_recognizers`.
4. **Define Fake Generation**: Update the `_generate` method in [src/pseudonymizer.py](file:///c:/Users/yramu/Desktop/PII_Scaler/src/pseudonymizer.py) to specify how to generate fake replacements.

No other code changes are needed!

---

## Running Web App & Deployment

### Running Web App
To run the FastAPI web service locally:
```bash
uvicorn web.app:app --host 0.0.0.0 --port 8000
```
Then navigate to `http://127.0.0.1:8000/` in your browser.

### Web Deployment
Hosted on Render's free tier — if idle for 15+ minutes, the first request may take up to ~50s to respond while the instance spins up.

---

## Observed Limitations & False Positives/Negatives

- **Technical PII Hits**: The document contains no actual SSNs, credit cards, or IP addresses. These recognizers were validated using synthetic test cases in the test suite and evaluation scripts.
- **Table Cell Boundaries (Address Recall FN)**: If a corporate address is split across cells (e.g., street details in Cell 1, city/PIN details in Cell 2), the tool only detects Cell 2 since the PIN code is located there; Cell 1 is missed. *Extension strategy (known limitation)*: When a PIN-anchored block is found near the start of a table cell with little preceding context, the system can be extended to check the immediately preceding sibling cell's text and merge it into the candidate block if not already claimed by another PII span.
- **Slash-Separated lists (Person Recall FN)**: In contact lists formatted with slashes (e.g. `Contact Person: Eric Bacha/ Sachin Gawade/ Pravin Teli/ ...`), spaCy's token parser is confused by the slashes and misses the middle names (unless they are promoters listed in the seed list).
- **Name Truncation (PERSON Recall FN)**: The small model `en_core_web_sm` occasionally truncates multi-token Indian names to the last 1-2 tokens (e.g., tagging `"Kushal Hegde"` instead of `"Rajesh Kushal Hegde"`). Names present in the promoter seed list are unaffected since they use exact string matching, not NER.
- **spaCy ORG Span Over-extension (Company FP/FN)**: Trimming ORG matches longer than 60 characters and matching against suffix patterns reduced false positives significantly. However, some common legal definitions (e.g. `"Board of Directors"`, `"Statutory Auditors"`) are still occasionally flagged as corporate entities by spaCy NER.

*(Note: Spaced PIN codes, list-aware telephone lists, and inverted name casing promoter seed list variants have been successfully resolved by the targeted heuristics in `src/recognizers.py` and `src/redactor.py`.)*

