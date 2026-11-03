"""
Darmstadt workbook audit — 00_data_audit/audit_workbook.py
Reads Data_CableTestSite_VerschaffelDrefkeetal2021.xlsx and writes a full
column-level audit to notes/darmstadt_workbook_audit.md.

Source: Verschaffel-Drefke et al. (2021), Energies 14, 7189.
Dataset: TUdatalib-665, CC BY-NC 4.0.
Verified: all numbers in the audit output traced to actual workbook cells [V].

Run from the proposal/ root:
    python code/00_data_audit/audit_workbook.py
"""
import pandas as pd
import numpy as np
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # proposal/
DATA_FILE = ROOT / "data" / "Data_CableTestSite_VerschaffelDrefkeetal2021.xlsx"
OUT_FILE  = ROOT / "notes" / "darmstadt_workbook_audit.md"

def audit():
    xl = pd.ExcelFile(DATA_FILE)
    L = [
        "# Darmstadt workbook audit (computed from the file)",
        f"File: `{DATA_FILE.name}`",
        f"Sheets: {xl.sheet_names}",
        "",
    ]

    for sh in xl.sheet_names:
        df = pd.read_excel(DATA_FILE, sheet_name=sh, header=None)
        L.append(f"\n## {sh}  (raw shape {df.shape})")

        if df.empty:
            L.append("(empty sheet)")
            continue

        if sh == "Basic Bedding Properties":
            L.append("```")
            L.append(df.dropna(how="all").dropna(axis=1, how="all").to_string(max_colwidth=26))
            L.append("```")
            continue

        if sh == "Load Profils":
            L.append("```")
            L.append(df.dropna(how="all").head(12).to_string(max_colwidth=26))
            L.append("```")

        data_start = 2 if sh == "Weather - Data - Temp" else 4
        hdr_rows = df.iloc[:data_start]
        labels = []
        for c in df.columns:
            parts = [
                str(hdr_rows.iloc[i, c]).strip()
                for i in range(min(data_start, 4))
                if pd.notna(hdr_rows.iloc[i, c])
            ]
            labels.append(" / ".join(parts))

        L.append(
            "| col | header | n | min | max | mean | n_missing(in span) |"
        )
        L.append("|---|---|---|---|---|---|---|")
        body = df.iloc[data_start:]

        for c in df.columns:
            if sh == "Weather - Data - Temp" and c == 1:
                s = pd.to_datetime(body[c], errors="coerce")
                n = int(s.notna().sum())
                if n:
                    L.append(f"| {c} | {labels[c]} | {n} | {s.min()} | {s.max()} | | |")
                continue

            s = pd.to_numeric(body[c], errors="coerce")
            n = int(s.notna().sum())
            if n == 0:
                continue
            first, last = s.first_valid_index(), s.last_valid_index()
            miss = int(s.loc[first:last].isna().sum())
            L.append(
                f"| {c} | {labels[c]} | {n} | {s.min():.4g} | {s.max():.4g}"
                f" | {s.mean():.4g} | {miss} |"
            )

        # time axis diagnostics
        for c in df.columns:
            if "Time" in labels[c] and sh != "Weather - Data - Temp":
                s = pd.to_numeric(body[c], errors="coerce").dropna()
                if len(s) > 5:
                    d = np.diff(s.values)
                    L.append(
                        f"\n- time column {c}: {len(s)} points, span "
                        f"{s.iloc[0]:.4g} to {s.iloc[-1]:.4g} d "
                        f"({s.iloc[-1]-s.iloc[0]:.2f} days), "
                        f"median step {np.median(d)*24*60:.2f} min, "
                        f"max step {d.max()*24*60:.1f} min, "
                        f"non-monotonic steps {(d<=0).sum()}"
                    )

        if sh == "Weather - Data - Temp":
            t = pd.to_datetime(body[1], errors="coerce").dropna()
            d = t.diff().dropna()
            L.append(
                f"\n- weather: {len(t)} stamps from {t.min()} to {t.max()}, "
                f"median step {d.median()}, "
                f"gaps > 1 h: {(d > pd.Timedelta(hours=1)).sum()}, "
                f"largest gap {d.max()}"
            )
            for yr, g in t.groupby(t.dt.year):
                L.append(f"  - {yr}: {len(g)} records")

    text = "\n".join(L)
    OUT_FILE.write_text(text, encoding="utf-8")
    print(f"Audit written to {OUT_FILE}")
    print(text[:3000])


if __name__ == "__main__":
    audit()
