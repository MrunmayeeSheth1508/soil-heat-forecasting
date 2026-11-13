"""SoilSens prototype UI.

    streamlit run app/streamlit_app.py

The UI only talks to soilsens.pipeline (assess / compare) and soilsens.forecast.
Swap a model in the backend and this file does not change.
"""
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from soilsens import config, data, provenance as P  # noqa: E402
from soilsens.forecast import gbt, gru  # noqa: E402
from soilsens.forecast.base import METHODS  # noqa: E402
from soilsens.physics.cable import CABLES, BEDDINGS  # noqa: E402
from soilsens.pipeline import Case, assess  # noqa: E402

st.set_page_config(page_title="SoilSens", layout="wide")

BADGE = {P.MEASURED: "#2e7d32", P.SPECIFIED: "#1565c0", P.ESTIMATED: "#ef6c00",
         P.FITTED: "#6a1b9a", P.SCENARIO: "#ad1457", P.CALCULATED: "#455a64"}


def badge(kind):
    return (f"<span style='background:{BADGE[kind]};color:white;border-radius:4px;"
            f"padding:1px 6px;font-size:0.75em'>{kind}</span>")


# ---------------------------------------------------------------- cached backend calls
@st.cache_data(show_spinner=False)
def stations():
    return [s for s in config.DEFAULT_STATIONS if s in data.list_stations(require_deep=False)]


@st.cache_data(show_spinner=False)
def issues_for(name):
    return [t.strftime("%Y-%m-%d %H:%M") for t in data.valid_issue_times(data.load_station(name))]


@st.cache_data(show_spinner="Running forecast, warm-up and current search...")
def run(case_dict):
    r = assess(Case(**case_dict))
    fc = r["forecast"]
    return {"traj": r["trajectory"], "summary": r["summary"], "support": r["support"],
            "fc_frame": fc.frame(), "fc_method": fc.method, "fc_prov": fc.provenance,
            "fc_note": fc.note, "hist": r["history_bg"],
            "warm_tc": r["warmup"].t_conductor}


@st.cache_data(show_spinner=False)
def station_frame(name):
    return data.load_station(name).frame()


# ---------------------------------------------------------------- sidebar: the case
st.sidebar.title("SoilSens")
st.sidebar.caption("Forecast-driven ampacity assessment · prototype, not for grid control")

stn_list = stations()
if not stn_list:
    st.error(f"No station files found in {config.data_dir()}. Set SOILSENS_DATA_DIR.")
    st.stop()
default_stn = stn_list.index("OK_Stillwater_2_W") if "OK_Stillwater_2_W" in stn_list else 0
station = st.sidebar.selectbox("Station (USCRN)", stn_list, index=default_stn)
iss_list = issues_for(station)
default_iss = next((i for i, t in enumerate(iss_list) if t.startswith("2021-07-15")), len(iss_list) - 1)
issue = st.sidebar.selectbox("Forecast issue time (LST)", iss_list, index=default_iss)

st.sidebar.subheader("Background forecast")
avail_methods = ["persistence", "diurnal"]
if any(gbt.is_trained(k) for k in range(4)):
    avail_methods.append("gbt")
if gru.HAVE_TORCH and gru.is_trained():
    avail_methods.append("gru")
method = st.sidebar.selectbox("Method", avail_methods, format_func=lambda m: METHODS[m])
stage = 3
if method == "gbt":
    trained = [k for k in range(4) if gbt.is_trained(k)]
    stage = st.sidebar.select_slider("Ablation stage", trained, value=trained[-1],
                                     format_func=lambda k: f"{k}: {gbt.STAGE_NAMES[k]}")
if not gbt.HAVE_SKLEARN:
    st.sidebar.warning("GBT unavailable: scikit-learn could not load on this computer "
                       f"({gbt.SKLEARN_ERROR[:80]}...). Baselines still work.")
elif "gbt" not in avail_methods:
    st.sidebar.caption("GBT not trained yet: `python scripts/train_gbt.py --stage all`")

st.sidebar.subheader("Installation")
cable = st.sidebar.selectbox("Cable construction", list(CABLES))
depth_opts = {"24 in cover (0.667 m centre)": 0.667, "30 in cover (0.819 m centre)": 0.819,
              "36 in (0.914 m centre)": 0.914}
depth_label = st.sidebar.selectbox("Burial depth", list(depth_opts), index=1)
in_duct = st.sidebar.checkbox("In 4 in PVC duct", value=True)
bedding = st.sidebar.selectbox("Bedding / backfill", list(BEDDINGS), index=2)
arrangement = st.sidebar.selectbox("Arrangement", ["Single cable (equivalent radial)",
                                                   "Trefoil / multiple cables (not yet)",
                                                   "2D cross-section (not yet)"])
if arrangement != "Single cable (equivalent radial)":
    st.sidebar.warning("Only the single-cable radial model is implemented. Running that instead.")

st.sidebar.subheader("Local moisture")
mmode = st.sidebar.radio("Mode", ["background only", "critical-isotherm drying"])
t_crit = st.sidebar.slider("Critical temperature for drying (°C)", 30, 80, 50,
                           disabled=mmode == "background only")

st.sidebar.subheader("Loading")
prior = st.sidebar.number_input("Previous load, held 168 h (A)", 0, 2000, 300, 10)
future = st.sidebar.number_input("Planned future load (A)", 0, 2000, 400, 10)
shape = st.sidebar.radio("Future load shape", ["flat", "daily cycle"], horizontal=True)
n_unc = st.sidebar.slider("Uncertainty resamples (0 = off)", 0, 30, 0, 5)

case = Case(station=station, issue=issue, method=method, stage=stage, cable=cable,
            depth_m=depth_opts[depth_label], in_duct=in_duct, bedding=bedding,
            moisture_mode=mmode, t_crit=float(t_crit), prior_current=float(prior),
            future_current=float(future), future_shape=shape, n_uncertainty=n_unc)

try:
    res = run(asdict(case))
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

S, traj = res["summary"], res["traj"]

# ---------------------------------------------------------------- header metrics
st.title("SoilSens: forecast-driven ampacity assessment")
st.caption(f"{station} · issued {issue} LST · {METHODS[method]}"
           + (f" (stage {stage})" if method == "gbt" else "") + " · "
           + res["support"]["geometry"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Permissible current, 72 h", f"{S['permissible_current_A']['value']:.0f} A")
c2.metric("Load multiplier on plan", f"{S['load_multiplier']['value']:.2f} ×")
c3.metric("Peak conductor temp (plan)", f"{S['peak_T_conductor_planned_C']['value']:.1f} °C",
          f"limit {S['T_max_C']['value']:.0f} °C", delta_color="off")
c4.metric("Minimum margin", f"{S['min_margin_K']['value']:.1f} K")
if S['load_multiplier']['value'] < 1:
    st.error("Planned load exceeds the permissible loading within the 72 h horizon.")

tabs = st.tabs(["Ground forecast", "Cable temperatures", "Rating", "Compare installations",
                "Forecast skill", "Provenance & downloads"])

# ---------------------------------------------------------------- 1. ground forecast
with tabs[0]:
    fcf = res["fc_frame"]
    df = station_frame(station)
    t0 = pd.Timestamp(issue)
    histw = df.loc[t0 - pd.Timedelta(hours=167):t0]
    var = st.radio("Variable", ["Temperature (°C)", "Moisture (m³/m³)"], horizontal=True)
    v = "T" if var.startswith("T") else "M"
    depths = st.multiselect("Depths (cm)", config.DEPTHS_CM, default=[20, 50, 100])
    fig = go.Figure()
    colors = dict(zip(config.DEPTHS_CM, ["#e53935", "#fb8c00", "#43a047", "#1e88e5", "#5e35b1"]))
    for d in depths:
        fig.add_trace(go.Scatter(x=histw.index, y=histw[f"{v}{d}"], name=f"{d} cm observed",
                                 line=dict(color=colors[d])))
        fig.add_trace(go.Scatter(x=fcf.index, y=fcf[f"{v}{d}_fc"], name=f"{d} cm forecast",
                                 line=dict(color=colors[d], dash="dash")))
        if f"{v}{d}_obs" in fcf:
            fig.add_trace(go.Scatter(x=fcf.index, y=fcf[f"{v}{d}_obs"], name=f"{d} cm later obs",
                                     line=dict(color=colors[d], width=1, dash="dot"), opacity=0.6))
    fig.add_vline(x=t0, line_dash="dot", line_color="grey")
    fig.update_layout(height=420, margin=dict(t=30), yaxis_title=var, hovermode="x unified")
    st.plotly_chart(fig, width="stretch")
    st.markdown(f"Forecast: **{res['fc_method']}** {badge(res['fc_prov'])} · {res['fc_note']} "
                f"Dotted lines are the later observations (hindcast check).", unsafe_allow_html=True)

    st.subheader("Background at cable depth")
    hi, hT, hM = res["hist"]
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=hi, y=hT, name="history (interp.)", line=dict(color="black")))
    fig2.add_trace(go.Scatter(x=traj.index, y=traj["T_background_fc"], name="forecast",
                              line=dict(color="#1e88e5", dash="dash")))
    if "T_background_obs" in traj:
        fig2.add_trace(go.Scatter(x=traj.index, y=traj["T_background_obs"], name="later obs",
                                  line=dict(color="grey", dash="dot")))
    fig2.update_layout(height=280, margin=dict(t=10), yaxis_title="°C")
    st.plotly_chart(fig2, width="stretch")
    st.caption(f"Linear interpolation between sensor depths to {case.depth_m} m. "
               "The background only enters the cable model through its outer boundary and "
               "initial state; it never overwrites the heated local ground.")

# ---------------------------------------------------------------- 2. cable temps
with tabs[1]:
    fig = go.Figure()
    for col, name, colr in [("T_conductor_planned", "Conductor", "#c62828"),
                            ("T_cable_surface_planned", "Cable surface", "#ef6c00"),
                            ("T_bedding_edge_planned", "Bedding edge", "#6d4c41"),
                            ("T_background_fc", "Background (forecast)", "#1e88e5")]:
        fig.add_trace(go.Scatter(x=traj.index, y=traj[col], name=name, line=dict(color=colr)))
    fig.add_hline(y=S["T_max_C"]["value"], line_dash="dash", line_color="red",
                  annotation_text="T_max")
    fig.update_layout(height=420, margin=dict(t=30), yaxis_title="°C", hovermode="x unified")
    st.plotly_chart(fig, width="stretch")
    a, b = st.columns(2)
    with a:
        f = go.Figure(go.Scatter(x=traj.index, y=traj["planned_current_A"], line=dict(color="black")))
        f.update_layout(height=240, margin=dict(t=30), title="Planned load (A)")
        st.plotly_chart(f, width="stretch")
    with b:
        f = go.Figure(go.Scatter(x=traj.index, y=traj["q_surface_W_m"], line=dict(color="#ef6c00")))
        f.update_layout(height=240, margin=dict(t=30), title="Heat leaving cable surface (W/m)")
        st.plotly_chart(f, width="stretch")
    st.caption(f"Conductor at issue time: {S['T_conductor_at_issue_C']['value']} °C after a "
               f"168 h warm-up at {prior:.0f} A. {res['support']['moisture']}.")

# ---------------------------------------------------------------- 3. rating
with tabs[2]:
    rows = [("Permissible constant current", S["permissible_current_A"])]
    if "permissible_current_obs_bg_A" in S:
        rows += [("Same, with observed background", S["permissible_current_obs_bg_A"]),
                 ("Effect of using the forecast", S["forecast_effect_A"])]
    if "permissible_current_p10_p90_A" in S:
        rows.append(("P10-P90 over forecast-error resamples", S["permissible_current_p10_p90_A"]))
    rows += [("Steady-state current (sanity check)", S["steady_state_current_A"]),
             ("Binding lead hour", S["binding_lead_h"])]
    for label, v in rows:
        st.markdown(f"**{label}:** {v['value']} {badge(v['provenance'])} "
                    f"<span style='color:grey;font-size:0.85em'>{v['source']}</span>",
                    unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=traj.index, y=traj["T_conductor_at_limit"],
                             name="Conductor at permissible current", line=dict(color="#c62828")))
    fig.add_hline(y=S["T_max_C"]["value"], line_dash="dash", line_color="red")
    fig.update_layout(height=360, margin=dict(t=30), yaxis_title="°C")
    st.plotly_chart(fig, width="stretch")
    st.caption("Largest constant current keeping the conductor at or below T_max at every "
               "hour of the 72 h horizon (bisection on the transient model).")

# ---------------------------------------------------------------- 4. compare
with tabs[3]:
    st.write("Change one thing; load, limits, history and forecast stay identical.")
    what = st.selectbox("Vary", ["Burial depth", "Bedding", "Duct", "Cable", "Forecast method"])
    if what == "Burial depth":
        alts = {k: replace(case, depth_m=v) for k, v in depth_opts.items()}
    elif what == "Bedding":
        alts = {k: replace(case, bedding=k) for k in BEDDINGS}
    elif what == "Duct":
        alts = {"In duct": replace(case, in_duct=True), "Direct buried": replace(case, in_duct=False)}
    elif what == "Cable":
        alts = {k: replace(case, cable=k) for k in CABLES}
    else:
        alts = {m: replace(case, method=m) for m in avail_methods}
    if st.button("Run comparison"):
        out = []
        for label, c in alts.items():
            r = run(asdict(c))["summary"]
            out.append({"option": label, "permissible current (A)": r["permissible_current_A"]["value"],
                        "peak conductor (°C)": r["peak_T_conductor_planned_C"]["value"],
                        "min margin (K)": r["min_margin_K"]["value"]})
        cmp = pd.DataFrame(out)
        f = go.Figure(go.Bar(x=cmp["option"], y=cmp["permissible current (A)"], marker_color="#1e88e5"))
        f.update_layout(height=320, margin=dict(t=30), yaxis_title="A")
        st.plotly_chart(f, width="stretch")
        st.dataframe(cmp, hide_index=True, width="stretch")

# ---------------------------------------------------------------- 5. skill
with tabs[4]:
    p = config.output_dir() / "ablation_summary.csv"
    if p.exists():
        summ = pd.read_csv(p)
        st.write("Median 72 h MAE on the test year (lower is better). Same issues for every method.")
        st.dataframe(summ, hide_index=True, width="stretch")
        st.caption("Produced by `python scripts/run_ablation.py`. GBT stages: "
                   + ", ".join(f"{k} {v}" for k, v in gbt.STAGE_NAMES.items()) + ".")
    else:
        st.info("No scores yet. Run `python scripts/run_ablation.py`.")

# ---------------------------------------------------------------- 6. provenance
with tabs[5]:
    tbl = pd.DataFrame([{"quantity": k, "value": str(v["value"]), "provenance": v["provenance"],
                         "source": v["source"]} for k, v in S.items()])
    st.dataframe(tbl, hide_index=True, width="stretch")
    st.markdown("**Model support**")
    st.json(res["support"])
    st.download_button("Trajectory CSV", traj.to_csv().encode(), f"trajectory_{station}_{issue[:10]}.csv")
    st.download_button("Forecast CSV", res["fc_frame"].to_csv().encode(), f"forecast_{station}_{issue[:10]}.csv")
    st.download_button("Case + summary JSON",
                       json.dumps({"case": asdict(case), "summary": S, "support": res["support"]},
                                  indent=2, default=str).encode(),
                       f"case_{station}_{issue[:10]}.json")
