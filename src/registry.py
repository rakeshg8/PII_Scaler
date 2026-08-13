import logging

PRIORITY = [
    "SSN",
    "CREDIT_CARD",
    "EMAIL",
    "PHONE",
    "IP_ADDRESS",
    "DATE_OF_BIRTH",
    "ADDRESS",
    "PERSON",
    "COMPANY"
]

class RecognizerRegistry:
    def __init__(self):
        self.recognizers = []

    def register(self, recognizer_func):
        self.recognizers.append(recognizer_func)

    def get_all_spans(self, text: str):
        spans = []
        for recognizer in self.recognizers:
            try:
                for span in recognizer(text):
                    if len(span) == 5:
                        start, end, entity_type, matched_text, confidence = span
                        if start >= end:
                            continue
                        spans.append(span)
            except Exception as e:
                logging.error(f"Error in recognizer: {e}")
        return spans

    def merge_spans(self, spans):
        """
        Merge overlapping spans based on priority order.
        Priority: SSN, CREDIT_CARD, EMAIL, PHONE, IP_ADDRESS, DATE_OF_BIRTH, PERSON, COMPANY, ADDRESS.
        If same priority, keep the longer one.
        """
        def sort_key(span):
            start, end, entity_type, _, _ = span
            length = end - start
            try:
                p_idx = PRIORITY.index(entity_type)
            except ValueError:
                p_idx = len(PRIORITY)
            return (p_idx, -length, start)

        sorted_spans = sorted(spans, key=sort_key)
        
        accepted_spans = []
        redacted_indices = set()

        for span in sorted_spans:
            start, end, entity_type, _, _ = span
            span_indices = set(range(start, end))
            if not (span_indices & redacted_indices):
                accepted_spans.append(span)
                redacted_indices.update(span_indices)

        return sorted(accepted_spans, key=lambda x: x[0])
