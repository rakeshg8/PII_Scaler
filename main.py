import argparse
import json
import os
import sys
import logging
from src.docx_io import read_docx, save_docx
from src.redactor import Redactor

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    parser = argparse.ArgumentParser(description="PII Redaction Tool for Word Documents (.docx)")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the input DOCX file"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to save the redacted DOCX file"
    )
    parser.add_argument(
        "--report",
        help="Path to save the JSON redaction report (optional)"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        logging.error(f"Input file not found: {args.input}")
        sys.exit(1)
        
    logging.info(f"Loading document: {args.input}")
    doc = read_docx(args.input)
    
    logging.info("Initializing Redactor and processing...")
    redactor = Redactor()
    redactions = redactor.redact_document(doc)
    
    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        
    logging.info(f"Saving redacted document: {args.output}")
    save_docx(doc, args.output)
    
    # Summarize redactions
    summary = {}
    for r in redactions:
        t = r['type']
        summary[t] = summary.get(t, 0) + 1
        
    logging.info(f"Redaction complete. Summary: {summary}")
    
    if args.report:
        logging.info(f"Saving report to: {args.report}")
        report_data = {
            "summary": summary,
            "redactions": redactions
        }
        with open(args.report, "w") as f:
            json.dump(report_data, f, indent=2)

if __name__ == "__main__":
    main()
