from fpdf import FPDF
import os

def create_pdf(filename, title, content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=title, ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    
    # Add content, handling line breaks
    for line in content.split('\n'):
        pdf.multi_cell(0, 10, txt=line)
    
    pdf.output(filename)

def main():
    os.makedirs("test_docs", exist_ok=True)
    
    # Document 1: Master Policy v1
    doc1 = """Acme Master Data Policy v1

Effective Date: 2024-01-01
Author: Compliance Department

1. Core Rules
All user data must be encrypted using AES-256.
Data retention is limited to 3 years.

Entities involved:
- Project Titan
- CloudStorage Pro
"""
    create_pdf("test_docs/acme_policy_v1.pdf", "Acme Master Data Policy v1", doc1)
    
    # Document 2: Master Policy v2 (Supersedes v1)
    doc2 = """Acme Master Data Policy v2

Effective Date: 2026-01-01
Author: Compliance Department

This document formally SUPERSEDES the "Acme Master Data Policy v1".

1. Core Rules
All user data must be encrypted using Quantum-Safe Encryption.
Data retention is limited to 1 year.

Entities involved:
- Project Titan
- CloudStorage Pro
"""
    create_pdf("test_docs/acme_policy_v2.pdf", "Acme Master Data Policy v2", doc2)
    
    # Document 3: Implementation Guide (Implements v2)
    doc3 = """Project Titan Implementation Guide

Author: Engineering Department

This guide IMPLEMENTS the "Acme Master Data Policy v2".

We will use Quantum-Safe Encryption across all databases.
The CloudStorage Pro API will be updated to delete logs after 1 year automatically.

Entities involved:
- Project Titan
- CloudStorage Pro
- AWS KMS
"""
    create_pdf("test_docs/acme_implementation_guide.pdf", "Project Titan Implementation Guide", doc3)

    # Document 4: Security Audit (Blocks Implementation)
    doc4 = """Security Audit Report 2026

Author: Security Operations

CRITICAL FINDING:
The current integration with AWS KMS is failing.
This open security vulnerability BLOCKS the "Project Titan Implementation Guide" from proceeding to production.

Entities involved:
- Project Titan
- AWS KMS
"""
    create_pdf("test_docs/acme_security_audit.pdf", "Security Audit Report 2026", doc4)
    
    print("Test PDFs generated successfully in the 'test_docs' directory.")

if __name__ == "__main__":
    main()
