"""
Darmstadt workbook quick inspector — 00_data_audit/inspect_workbook.py
Prints the first 14 rows of every sheet to stdout and writes a head-dump to
notes/darmstadt_workbook_head.txt.  Useful for a fast orientation before the
full audit.

Run from the proposal/ root:
    python code/00_data_audit/inspect_workbook.py
"""
import openpyxl
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data" / "Data_CableTestSite_VerschaffelDrefkeetal2021.xlsx"
OUT_FILE  = ROOT / "notes" / "darmstadt_workbook_head.txt"


def inspect():
    wb = openpyxl.load_workbook(DATA_FILE, data_only=True, read_only=True)
    out = []
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        nonempty = [r for r in rows if any(c is not None for c in r)]
        ncols = max((len(r) for r in nonempty), default=0)
        out.append(
            f"\n===== SHEET {ws.title!r}: {len(rows)} rows "
            f"(dims {ws.max_row}x{ws.max_column}), {len(nonempty)} non-empty"
        )
        for r in nonempty[:14]:
            out.append(" | ".join("" if c is None else str(c)[:38] for c in r[:14]))

    text = "\n".join(out)
    OUT_FILE.write_text(text, encoding="utf-8")
    print(f"Head dump written to {OUT_FILE}")
    print(text[:14000])


if __name__ == "__main__":
    inspect()
