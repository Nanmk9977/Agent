from __future__ import annotations
import argparse
import subprocess
import sys
import textwrap
from pathlib import Path
import logging
import importlib.util
import pandas as pd
import re
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ROOT = Path(__file__).parent.resolve()
CUSTOM_DIR = ROOT / "custom_parsers"
TESTS_DIR = ROOT / "tests"
DATA_DIR = ROOT / "data"
MAX_ATTEMPTS = 3

CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
TESTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------- Parser Template ----------------
PARSER_TEMPLATE = """from __future__ import annotations
import re
from typing import List
import pandas as pd
import pdfplumber

EXPECTED_COLUMNS = {expected_columns}

def _clean_cell(x: object) -> object:
    if x is None: return ""
    s = str(x).strip()
    s = re.sub(r"[₹$,]", "", s)
    s = re.sub(r"\\s+", " ", s)
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

{fallback_code}

    return pd.DataFrame(columns=EXPECTED_COLUMNS)
"""

# ---------------- Fallback code ----------------
def create_fallback_code(attempt: int) -> str:
    code = textwrap.dedent(r"""\
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
""")
    return textwrap.indent(code, "    ")


# ---------------- Write Test File ----------------
def write_test_file(target: str, pdf_path: Path, csv_path: Path):
    test_path = TESTS_DIR / f"test_{target}.py"
    test_code = f'''
import pandas as pd
from custom_parsers.{target}_parser import parse
expected = pd.read_csv(r"{csv_path}")

def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.fillna("")
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip().replace(r"\\s+", " ", regex=True)
    df = df.reindex(columns=expected.columns, fill_value="")
    return df

def test_parse_equals_expected():
    parsed = parse(r"{pdf_path}")
    assert _normalize(parsed).equals(_normalize(expected)), "Parsed DataFrame does not match expected CSV"
'''
    test_path.write_text(test_code, encoding="utf-8")
    return test_path

# ---------------- LangGraph Self-x Loop ----------------
def langgraph_generate_parser(target: str):
    target = target.lower()
    data_folder = DATA_DIR / target
    pdf_files = list(data_folder.glob("*.pdf"))
    csv_files = list(data_folder.glob("*.csv"))
    if not pdf_files or not csv_files:
        raise FileNotFoundError(f"No PDF/CSV found for {target} in {data_folder}")
    pdf_path, csv_path = pdf_files[0], csv_files[0]
    expected_df = pd.read_csv(csv_path)
    expected_columns = list(expected_df.columns)
    test_file = write_test_file(target, pdf_path, csv_path)

    for attempt in range(1, MAX_ATTEMPTS+1):
        logging.info(f"[LangGraph] Attempt {attempt} for parser '{target}'")
        fallback_code = create_fallback_code(attempt)
        parser_code = PARSER_TEMPLATE.replace("{fallback_code}", fallback_code)\
                                     .replace("{expected_columns}", repr(expected_columns))
        parser_path = CUSTOM_DIR / f"{target}_parser.py"
        parser_path.write_text(parser_code, encoding="utf-8")

        # Run pytest
        cmd = [sys.executable, "-m", "pytest", "-q", str(test_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logging.info(f"[LangGraph] Parser '{target}' passed tests successfully!")
            return
        else:
            logging.warning(f"[LangGraph] Test failed:\n{result.stdout}\n{result.stderr}")
            time.sleep(1)  # brief pause before retry
    raise RuntimeError(f"[LangGraph] Parser generation failed for '{target}' after {MAX_ATTEMPTS} attempts")

# ---------------- Streamlit UI ----------------
def run_streamlit():
    import streamlit as st
    st.title("Bank Statement Parser")
    uploaded_file = st.file_uploader("Upload your bank PDF", type=["pdf"])
    if uploaded_file:
        temp_pdf = Path("temp.pdf")
        temp_pdf.write_bytes(uploaded_file.getbuffer())
        bank = st.selectbox("Select Bank", ["ICICI", "SBI", "HDFC", "Axis"])
        parser_path = CUSTOM_DIR / f"{bank.lower()}_parser.py"
        if not parser_path.exists():
            st.warning(f"Parser for {bank} not found. Generating automatically...")
            try:
                langgraph_generate_parser(bank)
            except Exception as e:
                st.error(f"Parser generation failed: {e}")
                return
        try:
            spec = importlib.util.spec_from_file_location(f"{bank}_parser", parser_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"{bank}_parser"] = module
            spec.loader.exec_module(module)
            df = module.parse(str(temp_pdf))
            if df.empty:
                st.error("No data detected.")
            else:
                st.success("Parsing successful!")
                st.dataframe(df)
                st.download_button(
                    "Download CSV",
                    df.to_csv(index=False).encode("utf-8"),
                    file_name=f"{bank}_statement.csv"
                )
        except Exception as e:
            st.error(f"Error parsing PDF: {e}")

# ---------------- Main ----------------
def main():
    if "streamlit" in sys.modules:
        run_streamlit()
        return
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", help="Generate parser for this bank")
    args = parser.parse_args()
    if args.target:
        langgraph_generate_parser(args.target)
    else:
        print("Use --target <bank> to generate parser or run via Streamlit.")

if __name__ == "__main__":
    main()
