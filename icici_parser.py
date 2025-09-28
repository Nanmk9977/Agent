from __future__ import annotations
import re
from typing import List
import pandas as pd
import pdfplumber

EXPECTED_COLUMNS = ['Date', 'Description', 'Debit Amt', 'Credit Amt', 'Balance']

def _clean_cell(x: object) -> object:
    if x is None: return ""
    s = str(x).strip()
    s = re.sub(r"[₹$,]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s

def parse(pdf_path: str):
    import pandas as pd
    rows = []
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as doc:
            for page in doc.pages:
                tables = page.extract_tables() or []
                for tbl in tables:
                    if not tbl or len(tbl) < 2: continue
                    header = [_clean_cell(c) for c in tbl[0]]
                    data_rows = [[_clean_cell(c) for c in r] for r in tbl[1:]]
                    if any(ec.lower().split()[0] in " ".join(header).lower() for ec in EXPECTED_COLUMNS):
                        df = pd.DataFrame(data_rows, columns=header)
                        for col in EXPECTED_COLUMNS:
                            if col not in df.columns:
                                df[col] = ""
                        return df[EXPECTED_COLUMNS].reset_index(drop=True)
                    else:
                        rows.extend(data_rows)
    except Exception:
        pass

    \
    try:
        import pandas as pd
        import pdfplumber
        pages_text = []
        with pdfplumber.open(pdf_path) as doc:
            for page in doc.pages:
                pages_text.append(page.extract_text() or "")
        combined = "\n".join(pages_text)
        rows = []
        row_re = re.compile(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.{5,100})\s+([-\d,\.]+)", flags=re.M)
        for m in row_re.findall(combined):
            date, desc, amt = m
            rows.append([date.strip(), desc.strip(), amt.strip()])
        if rows:
            df = pd.DataFrame(rows, columns=EXPECTED_COLUMNS)
            return df[EXPECTED_COLUMNS].reset_index(drop=True)
    except Exception:
        pass


    return pd.DataFrame(columns=EXPECTED_COLUMNS)
