# Evaluation Report - PII Redaction Tool

This evaluation report documents the methodology, datasets, and performance metrics of the custom PII Redaction Tool developed for the Indian IPO Red Herring Prospectus (RHP) dataset.

## Evaluation Methodology

To evaluate the precision and recall of the redaction system honestly, a gold standard dataset was established using 16 pages/sections of real, full, verbatim running text extracted from `RHP.docx`.

### 1. Gold Dataset Structure (`evaluation/gold_annotations.json`)
The gold dataset contains 16 verbatim sections representing a mix of text styles, tables, and data types from the actual document:
- **page_1_promoters**: Promoter disclosures, lists of human names, and family trusts.
- **page_2_contact**: Registration details containing corporate office address, compliance officer name, landline, and email.
- **page_3_director_1** & **page_4_director_2**: Detailed Board of Directors tables containing names, designations, DIN numbers, and multi-line residential addresses.
- **page_5_registrar**: Registrar contact block containing corporate names, full multi-line address, PIN code, and phone numbers.
- **page_6_banker**: Banker contact block containing corporate names, multi-line address, and multiple phone numbers and email addresses.
- **page_7_auditor**: Statutory Auditor consent paragraphs containing corporate names.
- **page_8_share_acq**: Table rows containing acquisition dates (non-DOB) sitting directly next to promoter names.
- **page_9_neg_financials**: Financial ratios tables containing no PII, serving as a negative control.
- **page_10_neg_risk1** & **page_11_neg_risk2**: Risk factors prose paragraphs containing no PII, serving as negative controls.
- **page_12_exemptions**: Mentions of the subject company name ("KSH International Limited", "the Company", "the Issuer") alongside other companies to evaluate the exemption rules.
- **page_13_unusual_companies**: Injected unusual company names (e.g. "Kanj & Co. LLP", "Lalit Muljibhai Sarvaiya & Co.").
- **page_14_split_address**: Verbatim address split across cell boundaries (Cell 1: street info, Cell 2: Pune/PIN info).
- **page_15_casing_order**: Verbatim text with different casing or word order (e.g. "Hegde, Kushal Subbayya").
- **page_16_synthetic_pii**: Technical PII (SSNs, IPv4, IPv6, and Credit Cards) injected to evaluate regexes and the Luhn validation step.

### 2. Metrics Definition
Each detected span is evaluated against the gold annotations:
- **Span Match Criteria**: A detected span is counted as a **True Positive (TP)** if its Entity Type matches the gold label and the Intersection over Union (IoU) between the spans is greater than `0.5`.
- **False Positive (FP)**: Spans proposed by the tool that do not overlap with any gold label of the same type.
- **False Negative (FN)**: Gold annotations that the tool failed to detect.
- **Token-Level Accuracy**: Evaluated by classifying every space-separated token in the test text as `PII` or `Non-PII` based on overlap with gold vs. detected spans.

---

## Performance Results

Running the tool on the rebuilt gold dataset yields the following performance metrics:

| PII Type | TP | FP | FN | Precision | Recall | F1-Score |
|---|---|---|---|---|---|---|
| **SSN** | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **CREDIT_CARD** | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **EMAIL** | 8 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **PHONE** | 4 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **IP_ADDRESS** | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **DATE_OF_BIRTH** | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **ADDRESS** | 6 | 0 | 1 | 1.0000 | 0.8571 | 0.9231 |
| **PERSON** | 16 | 0 | 3 | 1.0000 | 0.8421 | 0.9143 |
| **COMPANY** | 14 | 15 | 4 | 0.4828 | 0.7778 | 0.5957 |
| **Overall** | **54** | **15** | **8** | **0.7826** | **0.8710** | **0.8244** |

- **Token-level Accuracy**: **94.01%** (1,209 / 1,286 tokens correct)

---

## Category-by-Category Analysis & Failure Modes

### 1. EMAIL, SSN, CREDIT_CARD, IP_ADDRESS, DATE_OF_BIRTH
- **Observation**: Achieved perfect F1-score (1.0).
- **Analysis**: Gating DOB detection by context triggers and validating credit card candidates using the Luhn algorithm prevents false positives. 

### 2. PHONE
- **Observation**: Achieved perfect F1-score (1.0).
- **Analysis**: List-aware context gating matches telephone numbers listed in lists (scanning forward from trigger labels until next trigger or sentence period), avoiding the previous false negative on long lists.

### 3. ADDRESS
- **Observation**: Precision = 1.0, Recall = 0.8571, F1 = 0.9231.
- **Analysis (False Negative)**: 
  - **Table Cell Boundaries**: The remaining missed address (FN=1) occurs on `page_14_split_address`, where the address text is split across sibling cells (`Cell 1: Registered Office: 11/3...` and `Cell 2: Pune – 411 501...`). Since the PIN code is in Cell 2, only Cell 2 is recognized, leaving Cell 1 un-redacted. This is a documented limitation of the system.
  - **Spaced PIN Codes**: Spaced PIN code matching works correctly now (yielding TPs on `Pune – 411 045`, `Pune – 411 004`, `Pune – 411 008`).

### 4. PERSON
- **Observation**: Precision = 1.0, Recall = 0.8421, F1 = 0.9143.
- **Analysis (False Negatives)**:
  - **Slash-Separated Lists**: On `page_6_banker` (`Contact Person: Eric Bacha/ Sachin Gawade/ Pravin Teli/ Siddharth Jadhav/ Tushar Gavankar`), the middle names (`Sachin Gawade`, `Pravin Teli`, `Siddharth Jadhav`) are missed. This occurs because the slashes confuse spaCy's sentence and token parsing, and they are not promoters so they are not in the seed list.
  - **Inverted Casing**: The inverted name `"Hegde, Kushal Subbayya"` is now perfectly matched and redacted due to generating name variants during promoter seed list construction. A lookup boundary prefix check successfully prevents inverted names from matching across list elements (crossover bug).

### 5. COMPANY
- **Observation**: Precision = 0.4828, Recall = 0.7778, F1 = 0.5957.
- **Analysis (False Positives & False Negatives)**:
  - **NER Over-extension**: Trimming spaCy ORG matches longer than 60 characters using the suffix regex and discarding them if no suffix is found successfully reduced COMPANY false positives from 24 down to 15. The remaining FPs represent short phrases (e.g. `"Board of Directors"`, `"Statutory Auditors"`) tagged as ORG by spaCy's legal/prospectus terminology confusion.
