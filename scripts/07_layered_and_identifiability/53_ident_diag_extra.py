import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""POST-HOC extra (not in the frozen list; flagged): do OBSERVED event-level changes in ln alpha track the change in forcing character, and does the wet-minus-control contrast survive adjusting for it?
Uses ident_diag_pairs.csv only (existing observed fits and window descriptors). Descriptive; cluster-robust SE; no causal claim."""
import sys, io, os, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace'); warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, statsmodels.formula.api as smf
from scipy.stats import spearmanr
P3 = (WS_ROOT + r'\phase3'); T = pd.read_csv(os.path.join(P3, 'ident_diag_pairs.csv')); L = []
T['wet'] = T.wet.astype(int); T['dgrad'] = np.log(T.grad2 / T.grad1); T['ddiur'] = np.log(T.diurnal2 / T.diurnal1); T['dsd5'] = np.log(T.sd5_2 / T.sd5_1)
def say(s=''): L.append(s); print(s)
say('POST-HOC EXTRA (observed fits only)')
say('\nMean change in forcing character between windows, by group (all usable pairs): log ratio post/control over stress')
for sp in ('dev', 'test'):
    d = T[T.split == sp]
    say(f'  {sp}: wetting: grad {d[d.wet == 1].dgrad.mean():+.2f}, diurnal fraction {d[d.wet == 1].ddiur.mean():+.2f}, SD T5 {d[d.wet == 1].dsd5.mean():+.2f} | control: grad {d[d.wet == 0].dgrad.mean():+.2f}, diurnal {d[d.wet == 0].ddiur.mean():+.2f}, SD T5 {d[d.wet == 0].dsd5.mean():+.2f}')
say('\nSpearman correlation of OBSERVED change in ln alpha with the change in forcing character')
for sp in ('dev', 'test'):
    for nm, d in (('all usable', T[T.split == sp]), ('retained', T[(T.split == sp) & T.ident]), ('rejected', T[(T.split == sp) & ~T.ident])):
        r1, r2 = spearmanr(d.d, d.dgrad), spearmanr(d.d, d.ddiur); say(f'  {sp} {nm:10s} n {len(d):3d}: vs change in |T5-T100| rho {r1.correlation:+.2f} (p {r1.pvalue:.2f}); vs change in diurnal fraction rho {r2.correlation:+.2f} (p {r2.pvalue:.2f})')
say('\nContrast (coefficient on wetting) before and after adjusting for the change in forcing character (OLS, cluster-robust SE; descriptive)')
for sp in ('dev', 'test'):
    for nm, d in (('all usable', T[T.split == sp]), ('retained', T[(T.split == sp) & T.ident])):
        d = d.dropna(subset=['dgrad', 'ddiur']); 
        for f, lab in (('d ~ wet', 'unadjusted'), ('d ~ wet + dgrad + ddiur', '+ forcing change')):
            m = smf.ols(f, d).fit(cov_type='cluster', cov_kwds={'groups': d.cluster}); say(f'  {sp} {nm:10s} {lab:18s}: wet coefficient {m.params["wet"]:+.3f} [{m.conf_int().loc["wet", 0]:+.3f}, {m.conf_int().loc["wet", 1]:+.3f}]  (n {len(d)})')
open(os.path.join(P3, 'ident_diag_extra.txt'), 'w', encoding='utf-8').write('\n'.join(L))
