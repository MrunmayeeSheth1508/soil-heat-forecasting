"""Parse Wilson et al. 2016 Supplemental_Table_T1.xls (FTP: ftp.atdd.noaa.gov/pub/wilson/)
and map coverage onto the 39 candidate stations. No model fitting."""
import re, xlrd, pandas as pd

s = xlrd.open_workbook('wilson/Supplemental_Table_T1.xls').sheet_by_index(0)
D = [0.05, 0.1, 0.2, 0.5, 1.0]
blocks = {'silt': 16, 'clay': 21, 'sand': 26, 'texclass': 31, 'wp1500': 43, 'fc33': 49, 'bd': 55}

def val(x):
    x = str(x).strip()
    if x in ('', 'n/a'): return (None, None)
    m = re.match(r'^([\d.]+)\s*(?:±\s*([\d.]+|n/a))?', x)
    if not m: return (x, None)
    sd = m.group(2)
    return (float(m.group(1)), None if sd in (None, 'n/a') else float(sd))

rows = []
for r in range(5, s.nrows):
    st, name = s.cell_value(r, 0), str(s.cell_value(r, 2)).strip()
    rec = dict(state=st, wname=name, installed=s.cell_value(r, 3), lat=s.cell_value(r, 5),
               lon=s.cell_value(r, 6), soil_depths=s.cell_value(r, 8),
               pits=' | '.join(str(s.cell_value(r, c)) for c in (9, 10, 11)))
    for k, c0 in blocks.items():
        for i, d in enumerate(D):
            v = s.cell_value(r, c0 + i)
            if k == 'texclass':
                rec[f'{k}_{d}'] = None if str(v).strip() in ('', 'n/a') else str(v).strip()
            else:
                m, sd = val(v)
                rec[f'{k}_{d}'] = m
                rec[f'{k}_{d}_sd'] = sd
    rows.append(rec)
W = pd.DataFrame(rows)
W['key'] = (W.state + '_' + W.wname.str.replace(r'\s+', '', regex=True)).str.upper()
W.to_csv('wilson/wilson_T1_tidy.csv', index=False)

cand = [re.match(r'^([A-Z]{2}_\S+)', l).group(1) for l in open('soil_lab_out.txt', encoding='utf8')
        if re.match(r'^[A-Z]{2}_\S+\s+\(', l)]
dev = ['TX_Muleshoe_19_S', 'SC_McClellanville_7_NE', 'IL_Champaign_9_SW', 'OK_Goodwell_2_SE',
       'NE_Lincoln_8_ENE', 'AL_Selma_13_WNW']

def ckey(c):
    st, rest = c.split('_', 1)
    return (st + '_' + rest.replace('_', '')).upper()

out = []
for c in cand:
    m = W[W.key == ckey(c)]
    r = dict(station=c, dev=c in dev, in_wilson=len(m) > 0)
    if len(m):
        m = m.iloc[0]
        for k in ('clay', 'sand', 'bd', 'fc33', 'wp1500'):
            got = [d for d in (0.05, 0.1, 0.2) if m[f'{k}_{d}'] is not None and not pd.isna(m[f'{k}_{d}'])]
            r[k] = ','.join(str(int(d * 100)) for d in got) or 'none'
        r['bd_5_10_20'] = '/'.join('-' if pd.isna(m[f'bd_{d}']) else f"{m[f'bd_{d}']:.2f}±{m[f'bd_{d}_sd']}" for d in (0.05, 0.1, 0.2))
        r['clay_5_10_20'] = '/'.join('-' if pd.isna(m[f'clay_{d}']) else f"{m[f'clay_{d}']:.0f}" for d in (0.05, 0.1, 0.2))
        r['installed'] = m.installed
    out.append(r)
O = pd.DataFrame(out)
O.to_csv('wilson/wilson_candidate_coverage.csv', index=False)
pd.set_option('display.width', 250)
print(O.to_string())
print('\ncandidates', len(O), 'in Wilson', O.in_wilson.sum())
full = O[(O.in_wilson) & (O.bd.str.contains('5,10,20', na=False)) & (O.clay.str.contains('5,10,20', na=False))]
print('full BD+texture at 5,10,20 cm:', len(full), list(full.station))
# near-name matches for unmatched candidates
for c in O[~O.in_wilson].station:
    st, loc = c.split('_', 1)
    town = loc.split('_')[0]
    hits = W[(W.state == st) & W.wname.str.contains(town, case=False)].wname.tolist()
    if hits: print('unmatched', c, '-> same-town Wilson entries:', hits)
