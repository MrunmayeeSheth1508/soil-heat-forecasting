import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""Issue-time inventory (spec: phase3/forecast/forecast_spec_frozen.md). NO scores are computed here. Outputs: phase3/forecast/issue_inventory.csv, inventory_summary.txt"""
import sys, io, os, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace'); warnings.filterwarnings('ignore')
sys.path.insert(0, WS_ROOT)
import numpy as np, pandas as pd
from forecastlib import *
FD = os.path.join(P3, 'forecast'); os.makedirs(FD, exist_ok=True)
stations = pd.read_csv(os.path.join(P3, 'stations_phase3.csv')).station.tolist()
rows = []
for stn in stations:
    st = Station(stn, None, None); df = st.df
    for third, ts in detect_spells(st):
        if ts not in df.index: continue
        i0 = df.index.get_loc(ts); v = validity(st, ts); past = df.iloc[max(i0 - 167, 0):i0 + 1]; fut = df.iloc[i0 + 1:i0 + 1 + HORIZON]
        doy = ts.dayofyear
        t5d = past['T5'].resample('D').mean()
        rain7 = float(past['P'].sum()) if past['P'].notna().mean() >= 0.9 else np.nan
        m10 = float(past['M10'].iloc[-24:].mean()) if past['M10'].iloc[-24:].notna().sum() >= 18 else np.nan
        dry = bool((rain7 <= 5.0) and (m10 <= st.m10_p40[doy])) if np.isfinite(rain7) and np.isfinite(m10) and np.isfinite(st.m10_p40[doy]) else np.nan
        nf = bool((t5d.iloc[:-1].dropna() > 1.0).all() and t5d.iloc[:-1].notna().sum() >= 5) if len(t5d) > 2 else np.nan
        nd = pd.date_range(ts.normalize() + pd.Timedelta(days=1), periods=3, freq='D'); hotn = st.hot.reindex(nd)
        rows.append(dict(station=stn, third_hot_day=third.date(), issue=ts, year=ts.year, split=('dev' if ts.year <= DEVYEARS[1] else 'val'), month=ts.month, mayseps=ts.month in (5, 6, 7, 8, 9),
                         dry_at_issue=dry, nonfreezing_past=nf, **v, T20_issue=last_valid(past, 'T20'), T50_issue=last_valid(past, 'T50'), T5_issue=last_valid(past, 'T5'), M10_issue=m10,
                         rain72_mm=float(fut['P'].sum()) if len(fut) else np.nan, rain72_ge10=bool(fut['P'].sum() >= 10) if len(fut) else np.nan, hot_days_next3=int(hotn.fillna(False).sum())))
    print(stn, 'spells so far', len(rows), flush=True)
I = pd.DataFrame(rows).sort_values('issue').reset_index(drop=True)
# operational date clusters (issue dates within 3 days chained across all stations; documented, not guaranteed independent)
cl = 0; last = None; ids = []
for s in I.issue.dt.normalize():
    if last is not None and (s - last).days > 3: cl += 1
    ids.append(cl); last = s
I['cluster'] = ids
I['common'] = I.init_ok & I.past_ok & I.anom_ok & I.out20_ok & I.out50_ok
I.to_csv(os.path.join(FD, 'issue_inventory.csv'), index=False)
L = []
def say(s=''): L.append(s); print(s)
say(f'ISSUE-TIME INVENTORY (no scores). stations {len(stations)}; detected spells {len(I)}; clusters {I.cluster.nunique()}')
say('\nSTAGE-WISE ATTRITION (counts of issues; the same common set is used for all competitors)')
for sp in ('dev', 'val', 'all'):
    d = I if sp == 'all' else I[I.split == sp]
    s1 = d[d.init_ok]; s2 = s1[s1.past_ok]; s3 = s2[s2.anom_ok]; s4 = s3[s3.out20_ok]; s5 = s3[s3.out20_ok & s3.out50_ok]
    say(f'{sp:4s}: detected {len(d)} (clusters {d.cluster.nunique()}, stations {d.station.nunique()}) -> five-depth profile at issue {len(s1)} -> 168 h coverage >= 80% {len(s2)} -> trailing-24h data {len(s3)} -> 20 cm outcome valid {len(s4)} -> BOTH depths valid = COMMON SET {len(s5)} (clusters {s5.cluster.nunique()}, stations {s5.station.nunique()})')
say('\nSTAND-ALONE REQUIREMENTS (what each competitor alone would need): persistence = profile at issue; anomaly baseline = profile + trailing 24 h; conduction = profile + 168 h coverage. Counts below are before the outcome-validity step.')
for sp in ('dev', 'val'):
    d = I[I.split == sp]; say(f'{sp}: persistence {int(d.init_ok.sum())}; anomaly {int((d.init_ok & d.anom_ok).sum())}; conduction {int((d.init_ok & d.past_ok).sum())}')
say('\nREASONS FOR MISSING OUTCOMES (among issues passing the input requirements): ')
inp = I[I.init_ok & I.past_ok & I.anom_ok]
for sp in ('dev', 'val'):
    d = inp[inp.split == sp]; say(f'{sp}: inputs ok {len(d)}; 20 cm outcome invalid {int((~d.out20_ok).sum())}; 50 cm outcome invalid {int((~d.out50_ok).sum())}; either {int((~(d.out20_ok & d.out50_ok)).sum())}')
C = I[I.common]
say('\nCOMMON SET: per split'); 
for sp in ('dev', 'val'):
    d = C[C.split == sp]
    say(f'{sp}: issues {len(d)}, clusters {d.cluster.nunique()}, stations {d.station.nunique()}; May-Sep {int(d.mayseps.sum())}; dry at issue {int((d.dry_at_issue == True).sum())}; non-freezing past week {int((d.nonfreezing_past == True).sum())}')
    say(f'   initial T20 median {d.T20_issue.median():.1f} C (range {d.T20_issue.min():.1f} to {d.T20_issue.max():.1f}); initial T50 median {d.T50_issue.median():.1f} C (range {d.T50_issue.min():.1f} to {d.T50_issue.max():.1f}); initial 10 cm moisture median {d.M10_issue.median():.2f} (range {d.M10_issue.min():.2f} to {d.M10_issue.max():.2f})')
    say(f'   recorded later outcomes (not used as filters): rain >= 10 mm within 72 h in {int((d.rain72_ge10 == True).sum())} issues; any rain {int((d.rain72_mm > 0).sum())}; at least one more hot day in the next 3 days: {int((d.hot_days_next3 > 0).sum())}')
say('\nissues per station in the common set (validation / development): ' + ', '.join(f'{s.split("_")[1]} {int((C[(C.station == s)].split == "val").sum())}/{int((C[(C.station == s)].split == "dev").sum())}' for s in sorted(C.station.unique())))
say('\nEVENTS BY MONTH (common set): ' + ', '.join(f'{m}:{int((C.month == m).sum())}' for m in range(1, 13)))
g = C.groupby('cluster').agg(n=('station', 'size'), st=('station', 'nunique'), span=('issue', lambda x: (x.max() - x.min()).days)); say(f'clusters: median events {g.n.median():.0f}, max events {g.n.max()}, max stations {g.st.max()}, longest chained span {g.span.max()} days')
open(os.path.join(FD, 'inventory_summary.txt'), 'w', encoding='utf-8').write('\n'.join(L))
