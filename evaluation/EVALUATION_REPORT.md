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

Running the tool on the rebuilt gold dataset (pinned to `spacy==3.7.5` and `en_core_web_sm==3.7.1`) yields the following performance metrics:

| PII Type | TP | FP | FN | Precision | Recall | F1-Score |
|---|---|---|---|---|---|---|
| **SSN** | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **CREDIT_CARD** | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **EMAIL** | 8 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **PHONE** | 4 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **IP_ADDRESS** | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **DATE_OF_BIRTH** | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| **ADDRESS** | 6 | 0 | 1 | 1.0000 | 0.8571 | 0.9231 |
| **PERSON** | 16 | 1 | 3 | 0.9412 | 0.8421 | 0.8889 |
| **COMPANY** | 14 | 18 | 4 | 0.4375 | 0.7778 | 0.5600 |
| **Overall** | **54** | **19** | **8** | **0.7397** | **0.8710** | **0.8000** |

- **Token-level Accuracy**: **93.16%** (1,198 / 1,286 tokens correct)

---

## Category-by-Category Analysis & Failure Modes

### 1. EMAIL, SSN, CREDIT_CARD, IP_ADDRESS, DATE_OF_BIRTH
- **Observation**: Achieved perfect F1-score (1.0).
- **Analysis**: These entities are highly structured. Luhn validation and trigger-phrase gating keep false positives at zero.

### 2. PHONE
- **Observation**: Achieved perfect F1-score (1.0).
- **Analysis**: List-aware context gating successfully scans forward from trigger labels in lists to match all numbers listed in a series.

### 3. ADDRESS
- **Observation**: Precision = 1.0, Recall = 0.8571, F1 = 0.9231.
- **Analysis (False Negative)**: The only missed address is on `page_14_split_address`, where the address is split across cells. Since the PIN is in Cell 2, Cell 1 is missed. This is a documented limitation.

### 4. PERSON
- **Observation**: Precision = 0.9412, Recall = 0.8421, F1 = 0.8889.
- **Analysis (False Negatives & False Positives)**:
  - **Model Truncation**: On `page_15_casing_order`, the name `"Rajesh K. Hegde"` was missed (False Negative) because the middle initial `"K."` bypassed the exact promoter seed list, and spaCy NER missed it.
  - **Role Misclassification**: On `page_2_contact`, `"Compliance Officer"` was incorrectly flagged as a `PERSON` by spaCy (False Positive).
  - **Slashes**: Slashes (e.g. `Eric Bacha/ Sachin Gawade/...`) confuse sentence/token boundaries, causing middle list elements to be missed by spaCy.
  - **Inverted Names**: `"Hegde, Kushal Subbayya"` is matched perfectly with 1.0 IoU due to inverted variant generation in the promoter seed booster.

### 5. COMPANY
- **Observation**: Precision = 0.4375, Recall = 0.7778, F1 = 0.5600.
- **Analysis (False Positives & False Negatives)**: Trimming ORG matches > 60 chars reduced FPs significantly. Remaining FPs represent short legal role/body definitions (e.g. `"Audit Committee"`, `"Board of Directors"`) incorrectly flagged as corporate names by spaCy.

---

## Observed Model Limitations

- **Name Truncation**: The small model `en_core_web_sm` occasionally truncates multi-token Indian names to the last 1-2 tokens (e.g. tagging `"Kushal Hegde"` instead of `"Rajesh Kushal Hegde"`). Names present in the promoter seed list are unaffected since they use exact string matching, not NER.
