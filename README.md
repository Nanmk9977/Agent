BANK PDF PARSER AI AGENT

This project is an AI-powered Bank PDF Parser that can extract structured data from bank statements in PDF format for ICICI and SBI banks. The parsed data can be viewed, analyzed, and downloaded as CSV. The system leverages custom parsers for each bank and provides a simple Streamlit-based UI for end-users.

FEATURES:
- Parses bank statements in PDF format for ICICI .
- Displays parsed data in a tabular format.
- Provides CSV download for extracted data.
- Optional balance trend visualization.
- Extensible to additional banks by adding custom parsers.

THE AGENT WORKS IN 5 STEPS:
1. Bank Selection & File Upload: User selects the bank and uploads a PDF statement via the Streamlit interface.  
2. Parser Dispatch: The agent routes the PDF to the corresponding parser (`icici_parser` or `sbi_parser`).  
3. PDF Extraction: Each parser extracts data using table detection and text recognition techniques.  
4. Data Normalization: Extracted data is cleaned, standardized, and organized into a DataFrame with columns: `Date`, `Description`, `Debit Amt`, `Credit Amt`, `Balance`.  
5. Output & Visualization: The agent displays the parsed table, provides CSV download, and optionally shows a line chart of account balance over time.

FLOW OF DIAGRAM:
<img width="987" height="316" alt="image" src="https://github.com/user-attachments/assets/cc9e87c6-1d15-4bdf-a2b2-388c279fd390" />

STRUCTURE:
AI_CHALLENGE/
├── icici/
│   ├── icici_parser.pdf
│   ├── icici_parser.csv
├── custom_parser/
│   ├── icici_parser.py
├── agent.py               
├── requirements.txt
├── README.md

