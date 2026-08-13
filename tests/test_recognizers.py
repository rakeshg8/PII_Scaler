import pytest
from src.recognizers import (
    recognize_email, recognize_phone, recognize_ssn, recognize_credit_card,
    recognize_ip_address, recognize_date_of_birth, recognize_address,
    make_person_recognizer, make_company_recognizer
)

def test_recognize_email():
    text = "Please contact support@example.com or user.name+tag@sub.domain.co for help."
    spans = list(recognize_email(text))
    assert len(spans) == 2
    assert spans[0][2] == "EMAIL"
    assert spans[0][3] == "support@example.com"
    assert spans[1][3] == "user.name+tag@sub.domain.co"

def test_recognize_phone():
    # Tier 1 with +91 (no context needed)
    text1 = "My number is +91 9876543210 and (+91-88888-77777)."
    spans1 = list(recognize_phone(text1))
    assert len(spans1) == 2
    assert all(s[2] == "PHONE" for s in spans1)
    
    # Tier 1 Landline (requires context)
    text2 = "Tel: 020-45051234. Without label 020-45051234."
    spans2 = list(recognize_phone(text2))
    assert len(spans2) == 1
    assert spans2[0][3] == "020-45051234"
    
    # Tier 2 Bare 10-digit (requires context)
    text3 = "Call Mobile 9876543210. Also registration id is 1234567890."
    spans3 = list(recognize_phone(text3))
    assert len(spans3) == 1
    assert spans3[0][3] == "9876543210"

def test_recognize_ssn():
    text = "SSN is 123-45-6789. Incorrect format: 12-345-6789."
    spans = list(recognize_ssn(text))
    assert len(spans) == 1
    assert spans[0][3] == "123-45-6789"

def test_recognize_credit_card():
    # Valid Luhn: 4111 1111 1111 1111 (sum is 30, mod 10 is 0)
    valid_cc = "4111 1111 1111 1111"
    invalid_cc = "4111 1111 1111 1112"
    
    text = f"Pay with {valid_cc} or {invalid_cc}."
    spans = list(recognize_credit_card(text))
    assert len(spans) == 1
    assert valid_cc in spans[0][3]

def test_recognize_ip_address():
    text = "IPv4: 192.168.1.1 and IPv6: 2001:db8:3333:4444:5555:6666:7777:8888."
    spans = list(recognize_ip_address(text))
    assert len(spans) == 2
    assert spans[0][3] == "192.168.1.1"
    assert spans[1][3] == "2001:db8:3333:4444:5555:6666:7777:8888"

def test_recognize_date_of_birth():
    text_pos = "My DOB is 15-08-1985. Also: date of birth August 20, 1990."
    text_neg = "The prospectus date is 10/12/2025. Financial year ended March 31, 2024."
    
    spans_pos = list(recognize_date_of_birth(text_pos))
    assert len(spans_pos) == 2
    
    spans_neg = list(recognize_date_of_birth(text_neg))
    assert len(spans_neg) == 0

def test_recognize_person():
    seed_names = {"Kushal Subbayya Hegde", "Pushpa Kushal Hegde"}
    recognizer = make_person_recognizer(seed_names)
    
    text = "Kushal Subbayya Hegde and Rajesh Kushal Hegde attended. SECTION II is NOT a person."
    spans = list(recognizer(text))
    
    matched_texts = [s[3] for s in spans]
    assert "Kushal Subbayya Hegde" in matched_texts
    assert "Rajesh Kushal Hegde" in matched_texts
    assert "SECTION II" not in matched_texts

def test_recognize_company():
    seed_orgs = {"Waterloo Industrial Park VI Private Limited"}
    recognizer = make_company_recognizer(seed_orgs)
    
    text = (
        "Waterloo Industrial Park VI Private Limited is one. "
        "Also check Infosys Ltd. and Wipro Limited. "
        "But never redact KSH International Limited or the Issuer."
    )
    spans = list(recognizer(text))
    matched_texts = [s[3] for s in spans]
    
    assert "Waterloo Industrial Park VI Private Limited" in matched_texts
    assert "Infosys Ltd." in matched_texts
    assert "Wipro Limited" in matched_texts
    assert "KSH International Limited" not in matched_texts
    assert "the Issuer" not in matched_texts

def test_recognize_address():
    text_valid1 = "Address: 201 Montreal Centre, Baner, Pune - 411045, Maharashtra, India."
    text_valid2 = "Registered office in Mumbai 400001, Maharashtra."
    text_invalid = "The pin code is 411001 but no state or country is mentioned."
    
    spans1 = list(recognize_address(text_valid1))
    assert len(spans1) == 1
    
    spans2 = list(recognize_address(text_valid2))
    assert len(spans2) == 1
    
    spans3 = list(recognize_address(text_invalid))
    assert len(spans3) == 0
