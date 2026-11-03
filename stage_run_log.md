# Earlier-stage execution log

| script | status | seconds | note |
|---|---|---|---|
| 01_inventory | FAILED (exit 1) | 0.8 | HTTPSConnection object at 0x000001A4856D32C0>: Failed to establish a new connection: [Errno 11001] getaddrinfo failed')) |
| 02_episode_audit | OK | 2.9 | ctable above USCRN's effective noise is not established. This is the central question Gate 3 must answer quantitatively. |
| 03_episode4_audit | OK | 0.4 |  signature at 20cm above the noise level?      This cannot be answered from the audit alone â€” needs the forward model. |
| 04_shallow_pilot | FAILED (exit 1) | 1.5 | ]             ~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~ ValueError: operands could not be broadcast together with shapes (4,) (5,) |
| 04b_shallow_pilot | OK | 69.2 | T20) are measured contemporaneously. Results do not establish literature gap, physical mechanism, or PINO justification. |
| 09_amplitude_check | OK | 26.9 |  575          3.20e-07            4.15e-07                    0.74    0.59- 1.17                     0.202          5.36 |
| 10_windowed_alpha | OK | 26.1 | e 0.034 Effective independent windows is far fewer than the window count: windows overlap by 50% and are autocorrelated. |
| 11_episode_table | OK | 0.4 | s mean(T5,T20): -0.587 Between-episode correlation of mean SM10 and mean T: -0.866  SM10 episode-means range 0.259 0.542 |
| 12_four_model_rerun | OK | 116.7 | ap 95% interval for b excludes 0 ([-0.157, +0.424]) -> False VERDICT: moisture effect NOT established beyond temperature |
| 13_multistation_download | SKIPPED |  | network download (NCEI) |
| 14_contrast_audit | OK | 80.1 | 3 -0.33 -0.32 -0.31 -0.31 -0.26  -0.24 -0.17 -0.03] Selma alone (dry informative days 2019-2021): r(theta, Tin) = -0.610 |
| 15_coverage | OK | 1.3 |  0.134  Within-site day pairs at the same 1 C Tin with /dtheta/ >= 0.10: 52337 total; stations with >=100 such pairs: 39 |
| 16_reconcile_qc_select | OK | 21.4 | teness   TX_Port_Aransas_32_NNE        stuck         CA_Merced_23_WSW        jumps CA_Yosemite_Village_12_W    amp_order |
| 17_multistation_pilot | OK | 112.2 | ust to boundary offsets: [0.043 0.05  0.045 0.048] -> True VERDICT: moisture contribution NOT established in development |
| 18_list_soil_products | SKIPPED |  | network (NCEI listing) |
| 19_read_soil01 | SKIPPED |  | network |
| 20_soilsip | SKIPPED |  | network download |
| 21_sda_probe | SKIPPED |  | network (USDA SDA) |
| 22_sda_probe2 | SKIPPED |  | network (USDA SDA) |
| 23_sda_projects | SKIPPED |  | network (USDA SDA) |
| 24_soil_lab_audit | FAILED (exit 1) | 2.0 | HTTPSConnection object at 0x000001DB17442C60>: Failed to establish a new connection: [Errno 11001] getaddrinfo failed')) |
| 25_bell_text | OK | 0.4 | er than the comparable trend (0.10Â°C decade âˆ’1 ) for air temperature ( Karl et al. 1995b ) and indicating the impo... |
| 26_wilson_table | OK | 1.4 | _13_W', 'NC_Asheville_8_SSW', 'NC_Durham_11_W'] unmatched OK_Goodwell_2_SE -> same-town Wilson entries: ['Goodwell 2 E'] |
| 27_pdf2txt | SKIPPED |  | needs PDFs at original external paths |
| 28_brunetti_xml | SKIPPED |  | reads C:\Users\jtani\Downloads xml |
| 29_citation_search | SKIPPED |  | network (literature APIs) |
| 30_audit15 | SKIPPED |  | reads files outside project |
| 31_phase3_download | SKIPPED |  | network download (NCEI) |
| 32_event_inventory | OK | 45.8 |  0                 0                    0 B totals: eligible days 73360, qualifying cells 582, stations with >=1 cell 38 |
| 33_thermal_check | OK | 5.0 | .0 (observed in 0.60) ordering: peak at 20 cm later than at 5 cm in 0.58, same day 0.42; 100 cm later than 20 cm in 0.85 |
| 34_lit_search | SKIPPED |  | network |
| 35_c_feasibility | FAILED (exit 1) | 835.4 | , name)            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ AttributeError: 'DataFrame' object has no attribute 'center_name' |
| 36_lit_search2 | SKIPPED |  | network |
| 37_extract_pages | SKIPPED |  | external PDFs |
| 38_lit_search3 | SKIPPED |  | network |
| 39_pilotA_solver_check | OK | 5.2 |  2.3907 phase 1.2044   nint  76 dt    900s amp 2.3937 phase 1.2057  ACCEPTANCE (amp err <= 3%, phase err <= 0.3 h): PASS |
| 40_pilotA_run | FAILED (exit 1) | 2.4 | odule>     MODE = sys.argv[1]; assert MODE in ('dev', 'test')            ~~~~~~~~^^^ IndexError: list index out of range |
| 41_extract_user_pdfs | SKIPPED |  | reads Downloads |
| 42_salvage_docx | SKIPPED |  | reads Downloads docx |
| 43_read_synthesis_v2 | SKIPPED |  | reads Downloads docx |
| 44_archive_and_repro_setup | SKIPPED |  | moves/archives workspace files (would disturb frozen archive) |
| 45_frozen_columns | OK | 2.9 | ce_8_NNW: not in Wilson table sha256 columns_frozen.csv 5a3589e207eadfe776f66aae0eb4778200d369fd360f5e94b2995b15dc079344 |
| 46_layered_diagnostic | FAILED (exit 1) | 2.5 | odule>     MODE = sys.argv[1]; assert MODE in ('dev', 'test')            ~~~~~~~~^^^ IndexError: list index out of range |
| 47_compare_repro | OK | 1.4 | th windows 21 (wet 12, ctrl 9); clusters 14    not identified: stress window only 15, post/ctrl window only 8, either 16 |
| 48_layered_verification | OK | 4.3 |  PASSED AT: base=False, refined=True, basic checks (1, 4, 5)=True GENERATOR RESOLUTION SELECTED BY VERIFICATION: refined |
| 49_layered_analysis | OK | 314.0 |   NaN   1.0 SD_Buffalo_13_ESE      0.019    NaN   3.0   NaN SD_Sioux_Falls_14_NNE -0.029  0.029   2.0   2.0 figure saved |
| 50_observed_selection_checks | OK | 19.6 | ta/ 0.64 vs identified 0.23; grid-edge fits among not-identified 1 of 16 share of events identified: wet 0.52, ctrl 0.64 |
| 51_layered_extra_stats | OK | 1.2 | ntral n  23: median /delta/ 0.06, SD 0.10, 90th percentile /delta/ 0.12, max /delta/ 0.29 combined event-level rows 2964 |
| 52_ident_diagnostic | OK | 104.9 |  retained n 14 rho -0.42 (p 0.13)     test S_central: all n 23 rho +0.28 (p 0.20); retained n 14 rho +0.19 (p 0.52) done |
| 53_ident_diag_extra | OK | 2.8 | nt +0.141 [-0.147, +0.429]  (n 21)   test retained   + forcing change  : wet coefficient +0.114 [-0.132, +0.361]  (n 21) |


## Addendum

- 40_pilotA_run.py dev: OK (40 s), pilotA_part1/2/3_dev.csv and pilotA_out_dev.txt identical to shipped.
- 46_layered_diagnostic.py dev: OK (96 s), 'reproduction of archived real-data event-level fits: checked 85, mismatches 0'; layered_events_dev.csv and layered_windows_dev.csv identical to shipped.
- 40/46 'test' not run (frozen run-once test sets).
- 35_c_feasibility: failed after 835 s on a missing center_name column (network data step); c_landcover.csv in workspace was overwritten, shipped copy in results/ is the original.
