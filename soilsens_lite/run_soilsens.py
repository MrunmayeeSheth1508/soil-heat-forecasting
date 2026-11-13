"""SoilSens Lite 3 - interactive assessment prototype. Plain Python 3.9+, no extra packages.

    python run_soilsens.py            # opens http://localhost:8501
    python run_soilsens.py --port 8600
    python run_soilsens.py --selftest # numerical and data checks, no browser

A small local web server (Python standard library) serves one HTML page; the page calls
the Python backend through /api/... endpoints. Every assessment is saved under runs/.
"""
import argparse
import csv
import json
import math
import sys
import threading
import time
import webbrowser
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from lite import core, pipeline, physics as ph, repo, darmstadt, live  # noqa: E402

CACHE = OrderedDict()          # run_id -> result (for the 2D field slider)


def clean(o):
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    return o


def meta():
    st = []
    for name in core.stations():
        s = core.index()[name]
        st.append({"name": name, "site": s.get("site", {}), "n_spells": len(core.spells_for(name))})
    cab = []
    for name, c in ph.CABLES().items():
        cab.append({"name": name, "t_max": c["t_max"], "t_emergency": c.get("t_emergency"),
                    "od_mm": round(c["layers"][-1][1] * 2000, 1), "used_in_pipeline": c.get("used_in_pipeline")})
    return {"stations": st, "methods": core.METHODS, "stages": core.STAGES, "presets": pipeline.presets(),
            "cables": cab, "beddings": {k: v["prov"] for k, v in ph.BEDDINGS.items()},
            "default": pipeline.DEFAULT_CASE, "version": pipeline.VERSION,
            "findings": FINDINGS, "gru_card": core.gru_card(), "live": live.STATE}


FINDINGS = [
    {"text": "Heat anomalies generally became smaller and peaked later with depth.",
     "source": "results/03_phase3_events_and_pilotA/thermal_check_out.txt (peak at 20 cm later than at 5 cm in 58% of spells; 100 cm later than 20 cm in 85%)"},
    {"text": "A shared simple moisture-diffusivity relationship did not transfer consistently between stations.",
     "source": "Stage 3, docs/PROJECT_HISTORY.md (multistation pilot)"},
    {"text": "A rain-linked change in soil thermal response was not confirmed; the estimate depended on model, selection rule and forcing.",
     "source": "Stages 6-7, docs/PROJECT_HISTORY.md"},
    {"text": "These findings motivated forecasting observed environmental conditions separately from modelling the cable's local disturbance.",
     "source": "Synthesis V4, sections 5 and 23"},
]


def skill():
    p = core.DATA / "ablation_summary.csv"
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(clean(body)).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                return self._send(200, (ROOT / "web" / "index.html").read_bytes(), "text/html; charset=utf-8")
            if u.path == "/api/meta":
                return self._send(200, meta())
            if u.path == "/api/spells":
                return self._send(200, core.spells_for(q["station"]))
            if u.path == "/api/soil":
                return self._send(200, core.spell_analysis(q["station"], q.get("spell"), q.get("start"), q.get("end")))
            if u.path == "/api/issues":
                s = core.station(q["station"])
                return self._send(200, {"issues": s.issue_times(), "gbt": s.gbt_issues,
                                        "spell_issues": [{"issue": x["issue"], "spell_id": x["spell_id"]}
                                                         for x in core.spells_for(q["station"]) if x["issue"]]})
            if u.path == "/api/skill":
                return self._send(200, skill())
            if u.path == "/api/repo":
                return self._send(200, repo.everything())
            if u.path == "/repo/forecast_figure.png":
                return self._send(200, (repo.REPO / "forecast_figure.png").read_bytes(), "image/png")
            if u.path == "/api/darmstadt/saved":
                return self._send(200, darmstadt.saved() or {})
            if u.path == "/api/darmstadt/mf3":
                return self._send(200, darmstadt.mf3_moisture())
            if u.path == "/api/darmstadt/moisture":
                return self._send(200, darmstadt.moisture_options())
            if u.path == "/api/runs":
                return self._send(200, pipeline.list_runs())
            if u.path == "/api/run":
                r = pipeline.load_run(q["id"])
                CACHE[r["run_id"]] = r
                return self._send(200, r)
            self._send(404, {"error": "not found"})
        except Exception as e:
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def do_POST(self):
        u = urlparse(self.path)
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
            if u.path == "/api/forecast":
                return self._send(200, core.forecast(body["station"], body["issue"], body.get("method", "persistence"),
                                                     int(body.get("stage", 3))))
            if u.path == "/api/assess":
                t = time.time()
                r = pipeline.assess(body)
                r["elapsed_s"] = round(time.time() - t, 2)
                CACHE[r["run_id"]] = r
                while len(CACHE) > 20:
                    CACHE.popitem(last=False)
                return self._send(200, r)
            if u.path == "/api/field":
                rid = body["run_id"]
                r = CACHE.get(rid) or pipeline.load_run(rid)
                return self._send(200, pipeline.field(r, int(body.get("hour", 24))))
            if u.path == "/api/install":
                c = pipeline.build_case(body)
                cable = ph.CABLES()[c["cable"]]
                m = ph.Mesh(cable, c["depth_m"], c["in_duct"], c["bedding"], c["bedding_radius_m"], c["arrangement"])
                return self._send(200, {"case": c, "inputs": pipeline.install_summary(c),
                                        "geometry": {"depth": c["depth_m"], "r_cable": m.r_cable, "r_bundle": m.r_bundle,
                                                     "r_bed": m.r_bed, "r_far": m.r_far, "in_duct": c["in_duct"],
                                                     "duct_id": ph.DUCT_ID, "duct_od": ph.DUCT_OD, "layers": cable["layers"],
                                                     "arrangement": c["arrangement"], "t_max": cable["t_max"],
                                                     "t_emergency": cable.get("t_emergency")}})
            if u.path == "/api/compare":
                return self._send(200, pipeline.compare(body["case"], body["what"]))
            if u.path == "/api/darmstadt/run":
                return self._send(200, darmstadt.reconstruct(body.get("bedding", "sand"), body.get("moisture", "undisturbed"),
                                                             bool(body.get("drying")), float(body.get("t_crit", 45))))
            self._send(404, {"error": "not found"})
        except Exception as e:
            self._send(500, {"error": f"{type(e).__name__}: {e}"})


def selftest():
    ok = True

    def check(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

    ks = [ph.conductivity(t / 100) for t in range(0, 41)]
    check("Johansen k increases with moisture", all(b >= a - 1e-12 for a, b in zip(ks, ks[1:])))
    for cname in (ph.DEFAULT_CABLE, darmstadt.CABLE):
        cable = ph.CABLES()[cname]
        for duct in (True, False):
            mesh = ph.Mesh(cable, 0.8, duct, "FTB (fluidized thermal backfill)")
            I = ph.steady_ampacity(cable, mesh, 15.0, 0.25)
            sim = ph.simulate(cable, mesh, [15.0] * 4800, [0.25] * 4800, [I] * 4800, dt=3600)
            check(f"transient -> steady T_max ({cname[:14]}, duct={duct})", abs(sim["tc"][-1] - cable["t_max"]) < 0.5)
    cable = ph.CABLES()[ph.DEFAULT_CABLE]
    mesh = ph.Mesh(cable, 0.819, True, "FTB (fluidized thermal backfill)")
    sim = ph.simulate(cable, mesh, [15.0] * 4800, [0.25] * 4800, [500.0] * 4800, dt=3600)
    check("energy balance at steady state", abs(sim["qs"][-1] - sim["ql"][-1]) / sim["ql"][-1] < 0.01)
    mt = ph.Mesh(ph.CABLES()[darmstadt.CABLE], 0.623, False, "Darmstadt sand", arrangement="trefoil", uniform=True, theta_bed=0.1)
    sim = ph.simulate(ph.CABLES()[darmstadt.CABLE], mt, [15.0] * 4800, [0.1] * 4800, [300.0] * 4800, dt=3600)
    check("trefoil: centre cable carries 1/3 of the bundle's losses at steady state",
          abs(sim["ql"][-1] - 3 * sim["qs"][-1]) / sim["ql"][-1] < 0.01)
    sim = ph.simulate(cable, mesh, [12.0] * 48, [0.2] * 48, [0.0] * 48)
    check("zero current stays at background", max(abs(v - 12.0) for v in sim["tc"]) < 1e-6)
    b = {r["code"]: r for r in repo.benchmark()["val"]["table"]}
    reported = {"B1": (0.740, 0.274), "B2": (0.708, 0.352), "C1": (0.704, 0.333),
                "C2": (0.673, 0.316), "C3": (0.704, 0.334), "RECON": (0.262, 0.198)}
    check("repo stage-8 benchmark recomputed = reported numbers",
          all(abs(b[k]["T20_h72"] - v[0]) < 0.0015 and abs(b[k]["T50_h72"] - v[1]) < 0.0015 for k, v in reported.items()))
    check(f"heat-spell archive loaded ({len(core.spells())} spells, "
          f"{sum(1 for s in core.spells() if s['issue'])} with forecast issues)", len(core.spells()) > 0)
    t = time.time()
    r = pipeline.assess({}, save=False)
    check(f"full assessment runs ({time.time() - t:.1f}s), I = {r['summary']['permissible_current_A']['value']} A",
          r["summary"]["permissible_current_A"]["value"] > 0)
    if live.STATE["enabled"]:
        pre = core.station("NE_Lincoln_8_ENE").gbt("2021-08-27 08:00", model="gru")
        lv = core.forecast("NE_Lincoln_8_ENE", "2021-08-27 08:00", "gru")["T"]
        check("live GRU matches the precomputed GRU forecast (max diff < 0.01 C)",
              max(abs(a - b) for ra, rb in zip(pre[0], lv) for a, b in zip(ra, rb) if math.isfinite(a) and math.isfinite(b)) < 0.01)
    g = core.forecast("NE_Lincoln_8_ENE", "2021-08-27 08:00", "gru")
    check("GRU forecast loads (72 h x 5 depths, finite)", len(g["T"]) == 72 and all(math.isfinite(v) for v in g["T"][0][2:]))
    d = darmstadt.reconstruct("fluidized_backfill")
    check(f"Darmstadt reconstruction runs (FBF MAE {d['stats']['mae_K']} K)", d["stats"]["n_compared"] > 500)
    print("ALL PASSED" if ok else "SOME CHECKS FAILED")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8501)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--live", action="store_true",
                    help="run the trained tree/GRU models live (needs the full backend, e.g. in Codespaces)")
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    st = live.enable(a.live)
    if a.live:
        print(("LIVE MODE ON: " if st["enabled"] else "Live mode unavailable, using precomputed forecasts: ") + st["reason"])
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    url = f"http://localhost:{a.port}"
    print(f"SoilSens Lite 3 running at {url}   (press Ctrl+C to stop)")
    if not a.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
