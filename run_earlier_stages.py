"""Execute earlier-stage scripts inside workspace/ in project order; record exit status, runtime and tail of output.
Skipped on purpose (documented in RUN_ORDER.md): scripts that download from the network or rewrite/archive the workspace,
and scripts that read files outside the project.
Output: stage_run_log.json / stage_run_log.md
"""
import os, sys, glob, json, subprocess, time
H = os.path.dirname(os.path.abspath(__file__))
env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
ORDER = ['01_inventory','02_episode_audit','03_episode4_audit','04_shallow_pilot','04b_shallow_pilot',
         '09_amplitude_check','10_windowed_alpha','11_episode_table','12_four_model_rerun',
         '14_contrast_audit','15_coverage','16_reconcile_qc_select','17_multistation_pilot',
         '24_soil_lab_audit','25_bell_text','26_wilson_table',
         '32_event_inventory','33_thermal_check','35_c_feasibility','39_pilotA_solver_check','40_pilotA_run',
         '45_frozen_columns','46_layered_diagnostic','47_compare_repro','48_layered_verification','49_layered_analysis',
         '50_observed_selection_checks','51_layered_extra_stats','52_ident_diagnostic','53_ident_diag_extra']
SKIP = {'13_multistation_download':'network download (NCEI)','31_phase3_download':'network download (NCEI)',
        '18_list_soil_products':'network (NCEI listing)','19_read_soil01':'network','20_soilsip':'network download',
        '21_sda_probe':'network (USDA SDA)','22_sda_probe2':'network (USDA SDA)','23_sda_projects':'network (USDA SDA)',
        '27_pdf2txt':'needs PDFs at original external paths','28_brunetti_xml':'reads C:\\Users\\jtani\\Downloads xml',
        '29_citation_search':'network (literature APIs)','30_audit15':'reads files outside project',
        '34_lit_search':'network','36_lit_search2':'network','37_extract_pages':'external PDFs','38_lit_search3':'network',
        '41_extract_user_pdfs':'reads Downloads','42_salvage_docx':'reads Downloads docx','43_read_synthesis_v2':'reads Downloads docx',
        '44_archive_and_repro_setup':'moves/archives workspace files (would disturb frozen archive)'}
TIMEOUT = int(os.environ.get('STAGE_TIMEOUT', '1500'))
paths = {os.path.splitext(os.path.basename(f))[0]: f for f in glob.glob(os.path.join(H, 'scripts', '**', '*.py'), recursive=True)}
log = []
for name in ORDER:
    f = paths.get(name)
    if not f: log.append(dict(script=name, status='NOT FOUND')); continue
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, f], env=env, capture_output=True, text=True, timeout=TIMEOUT, cwd=os.path.join(H, 'workspace'))
        st = 'OK' if r.returncode == 0 else f'FAILED (exit {r.returncode})'
        tail = (r.stdout[-400:] if r.returncode == 0 else r.stderr[-700:]).strip()
    except subprocess.TimeoutExpired:
        st, tail = f'TIMEOUT >{TIMEOUT}s', ''
    log.append(dict(script=name, status=st, seconds=round(time.time() - t0, 1), tail=tail))
    print(name, st, round(time.time() - t0), 's', flush=True)
    json.dump(log, open(os.path.join(H, 'stage_run_log.json'), 'w'), indent=1)
for k, v in SKIP.items(): log.append(dict(script=k, status='SKIPPED', reason=v))
json.dump(log, open(os.path.join(H, 'stage_run_log.json'), 'w'), indent=1)
with open(os.path.join(H, 'stage_run_log.md'), 'w', encoding='utf-8') as o:
    o.write('# Earlier-stage execution log\n\n| script | status | seconds | note |\n|---|---|---|---|\n')
    for e in sorted(log, key=lambda e: e['script']):
        note = e.get('reason', '') or (e.get('tail', '')[-120:].replace('\n', ' ').replace('|', '/'))
        o.write(f"| {e['script']} | {e['status']} | {e.get('seconds','')} | {note} |\n")
print('done')
