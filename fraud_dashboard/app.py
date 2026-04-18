"""
Tableau de bord — transactions scorées (Kafka ``bank.transactions.scored``).

  PYTHONPATH=. streamlit run fraud_dashboard/app.py

Variables utiles : ``KAFKA_BOOTSTRAP_SERVERS``, ``KAFKA_TOPIC_SCORED``,
``DASHBOARD_KAFKA_GROUP`` (défaut : fraud-dashboard-ui).
"""
from __future__ import annotations

import os
import time
from collections import deque
from datetime import timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from Config.config import BOOTSTRAP_SERVERS, TOPIC_SCORED
from fraud_dashboard.data import demo_batch, make_consumer, poll_records

MAX_BUFFER = 5000
FRAGMENT_INTERVAL_S = 2.0


def _env(name: str, default: str) -> str:
    v = os.environ.get(name, "").strip()
    return v if v else default


def inject_style() -> None:
    st.markdown(
        """
        <style>
          .main-header {
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: #f8fafc;
            margin-bottom: 0.15rem;
          }
          .sub-header {
            font-size: 0.95rem;
            color: #94a3b8;
            margin-bottom: 1.25rem;
          }
          div[data-testid="stMetricValue"] {
            font-variant-numeric: tabular-nums;
          }
          .rt-count-wrap {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0b1220 100%);
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 1.25rem 1.5rem 1.1rem 1.5rem;
            margin-bottom: 1rem;
          }
          .rt-count-big {
            font-size: clamp(2.5rem, 6vw, 3.75rem);
            font-weight: 800;
            line-height: 1.05;
            letter-spacing: -0.03em;
            color: #38bdf8;
            font-variant-numeric: tabular-nums;
          }
          .rt-count-label {
            font-size: 0.95rem;
            color: #94a3b8;
            margin-top: 0.35rem;
          }
          .rt-count-meta {
            font-size: 0.8rem;
            color: #64748b;
            margin-top: 0.5rem;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner=False)
def kafka_consumer_resource(bootstrap: str, topic: str, group_id: str):
    return make_consumer(bootstrap, topic, group_id)


def buffer_to_dataframe(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if "_ingested_at" in df.columns:
        df["_ts"] = pd.to_datetime(df["_ingested_at"], unit="s")
    if "fraud_score" in df.columns:
        df["fraud_score"] = pd.to_numeric(df["fraud_score"], errors="coerce")
    if "fraud_predicted" in df.columns:
        df["fraud_predicted"] = pd.to_numeric(df["fraud_predicted"], errors="coerce").fillna(0).astype(int)
    return df


def empty_chart(message: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0f172a",
        margin=dict(l=48, r=24, t=48, b=48),
        height=360,
        annotations=[
            dict(
                text=message,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=14, color="#64748b"),
            )
        ],
    )
    return fig


def fig_timeseries(df: pd.DataFrame) -> go.Figure:
    if df.empty or "_ts" not in df.columns:
        return empty_chart("En attente de données…")
    d = df.sort_values("_ts").copy()
    d["minute"] = d["_ts"].dt.floor("min")
    g = d.groupby("minute", as_index=False).agg(
        n=("_ts", "count"),
        frauds=("fraud_predicted", "sum"),
    )
    g["rate_pct"] = (g["frauds"] / g["n"].clip(lower=1) * 100.0).round(2)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=g["minute"], y=g["n"], name="Volume / min", marker_color="#334155"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=g["minute"],
            y=g["rate_pct"],
            name="% alertes / min",
            mode="lines+markers",
            line=dict(color="#f97316", width=2),
            marker=dict(size=6),
        ),
        secondary_y=True,
    )
    fig.update_yaxes(title_text="Transactions", secondary_y=False, gridcolor="#1e293b")
    fig.update_yaxes(title_text="% détecté", secondary_y=True, range=[0, 105], gridcolor="#1e293b")
    fig.update_xaxes(gridcolor="#1e293b")
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0f172a",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=48, r=48, t=32, b=48),
        height=420,
    )
    return fig


def fig_score_dist(df: pd.DataFrame) -> go.Figure:
    if df.empty or "fraud_score" not in df.columns:
        return empty_chart("Pas encore de scores.")
    s = df["fraud_score"].dropna()
    if s.empty:
        return empty_chart("Pas encore de scores.")
    sub = df.dropna(subset=["fraud_score"])
    if "fraud_predicted" in sub.columns:
        fig = px.histogram(
            sub,
            x="fraud_score",
            color="fraud_predicted",
            nbins=40,
            color_discrete_map={0: "#38bdf8", 1: "#fb7185"},
            labels={"fraud_score": "Score (probabilité classe fraude)", "count": "Effectif"},
        )
    else:
        fig = px.histogram(
            sub,
            x="fraud_score",
            nbins=40,
            labels={"fraud_score": "Score (probabilité classe fraude)", "count": "Effectif"},
        )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0f172a",
        bargap=0.08,
        margin=dict(l=48, r=24, t=48, b=48),
        height=380,
        legend_title_text="Prédit fraude",
    )
    return fig


def fig_by_type(df: pd.DataFrame) -> go.Figure:
    if df.empty or "transaction_type" not in df.columns:
        return empty_chart("Type de transaction manquant.")
    g = (
        df.groupby("transaction_type", as_index=False)
        .agg(volume=("_ts", "count"), frauds=("fraud_predicted", "sum"))
        .sort_values("volume", ascending=False)
    )
    g["ok"] = g["volume"] - g["frauds"]
    fig = go.Figure(
        data=[
            go.Bar(name="Légitime", x=g["transaction_type"], y=g["ok"], marker_color="#22c55e"),
            go.Bar(name="Alerte", x=g["transaction_type"], y=g["frauds"], marker_color="#ef4444"),
        ]
    )
    fig.update_layout(
        template="plotly_dark",
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0f172a",
        margin=dict(l=48, r=24, t=48, b=48),
        height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(gridcolor="#1e293b"),
        xaxis=dict(gridcolor="#1e293b"),
    )
    return fig


def live_poll(
    demo: bool,
    bootstrap: str,
    topic: str,
    group_id: str,
    rng_batch: int,
) -> None:
    buf: deque = st.session_state["rows"]
    n_before = len(buf)
    if demo:
        for row in demo_batch(rng_batch):
            buf.append(row)
        st.session_state["kafka_error"] = None
    else:
        try:
            cons = kafka_consumer_resource(bootstrap, topic, group_id)
            for row in poll_records(cons, max_messages=256):
                buf.append(row)
            st.session_state["kafka_error"] = None
        except Exception as e:
            st.session_state["kafka_error"] = str(e)
    added = len(buf) - n_before
    st.session_state["last_poll_added"] = int(added)
    st.session_state["total_ingested"] = int(st.session_state.get("total_ingested", 0)) + int(added)
    st.session_state["last_poll_ts"] = time.time()


def _defaults() -> None:
    if "rows" not in st.session_state:
        st.session_state["rows"] = deque(maxlen=MAX_BUFFER)
    if "kafka_error" not in st.session_state:
        st.session_state["kafka_error"] = None
    if "dash_demo" not in st.session_state:
        st.session_state["dash_demo"] = False
    if "dash_bootstrap" not in st.session_state:
        st.session_state["dash_bootstrap"] = _env("KAFKA_BOOTSTRAP_SERVERS", BOOTSTRAP_SERVERS)
    if "dash_topic" not in st.session_state:
        st.session_state["dash_topic"] = _env("KAFKA_TOPIC_SCORED", TOPIC_SCORED)
    if "dash_group" not in st.session_state:
        st.session_state["dash_group"] = _env("DASHBOARD_KAFKA_GROUP", "fraud-dashboard-ui")
    if "dash_demo_n" not in st.session_state:
        st.session_state["dash_demo_n"] = 4
    if "total_ingested" not in st.session_state:
        st.session_state["total_ingested"] = 0
    if "last_poll_added" not in st.session_state:
        st.session_state["last_poll_added"] = 0
    if "last_poll_ts" not in st.session_state:
        st.session_state["last_poll_ts"] = None


@st.fragment(run_every=timedelta(seconds=FRAGMENT_INTERVAL_S))
def poll_fragment() -> None:
    live_poll(
        bool(st.session_state.get("dash_demo")),
        str(st.session_state.get("dash_bootstrap", BOOTSTRAP_SERVERS)),
        str(st.session_state.get("dash_topic", TOPIC_SCORED)),
        str(st.session_state.get("dash_group", "fraud-dashboard-ui")),
        int(st.session_state.get("dash_demo_n", 4)),
    )


def main() -> None:
    st.set_page_config(
        page_title="FraudShield — Surveillance",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_style()
    _defaults()

    st.markdown('<p class="main-header">FraudShield Analytics</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Flux temps réel · topic Kafka scoré · speed path (Lambda)</p>',
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### Connexion")
        st.toggle("Mode démo (sans Kafka)", key="dash_demo")
        st.text_input("Bootstrap Kafka", key="dash_bootstrap")
        st.text_input("Topic scoré", key="dash_topic")
        st.text_input("Groupe consommateur", key="dash_group")
        st.slider("Transactions démo / cycle", 1, 12, key="dash_demo_n")
        st.caption(
            f"Rafraîchissement données : {FRAGMENT_INTERVAL_S:.0f} s. "
            "Démarrez **simulateur-api**, **fraud-scorer**, puis ce service."
        )
        if st.button("Vider le tampon"):
            st.session_state["rows"].clear()
            st.session_state["kafka_error"] = None
            st.rerun()
        if st.button("Réinitialiser le compteur temps réel"):
            st.session_state["total_ingested"] = 0
            st.session_state["last_poll_added"] = 0
            st.session_state["last_poll_ts"] = None
            st.rerun()

    poll_fragment()

    err = st.session_state.get("kafka_error")
    if err and not st.session_state.get("dash_demo"):
        st.warning(f"Kafka : {err}")

    rows = list(st.session_state["rows"])
    df = buffer_to_dataframe(rows)

    total_rx = int(st.session_state.get("total_ingested", 0))
    last_add = int(st.session_state.get("last_poll_added", 0))
    last_ts = st.session_state.get("last_poll_ts")
    ts_txt = (
        time.strftime("%H:%M:%S", time.localtime(last_ts))
        if isinstance(last_ts, (int, float))
        else "—"
    )

    st.markdown(
        f"""
        <div class="rt-count-wrap">
          <div class="rt-count-big">{total_rx:,}</div>
          <div class="rt-count-label">Transactions reçues en temps réel (cumul session · topic scoré)</div>
          <div class="rt-count-meta">Dernière fenêtre : +{last_add} · horodatage poll : {ts_txt} · rafraîchissement ~{FRAGMENT_INTERVAL_S:.0f} s</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    n = len(df)
    frauds = int(df["fraud_predicted"].sum()) if n and "fraud_predicted" in df.columns else 0
    rate = (frauds / n * 100.0) if n else 0.0
    avg_score = 0.0
    if n and "fraud_score" in df.columns and "fraud_predicted" in df.columns:
        m = df.loc[df["fraud_predicted"] == 1, "fraud_score"].mean()
        avg_score = float(m) if pd.notna(m) else 0.0
    c1.metric(
        "Tampon affiché (max " + str(MAX_BUFFER) + ")",
        f"{n:,}".replace(",", " "),
        help="Nombre de lignes actuellement conservées pour les graphiques (les plus anciennes peuvent être évincées).",
    )
    c2.metric("Alertes (prédiction)", f"{frauds:,}".replace(",", " "))
    c3.metric("Taux d’alerte", f"{rate:.2f} %")
    c4.metric("Score moyen (alertes)", f"{avg_score:.3f}")

    g1, g2 = st.columns([1.15, 0.85])
    with g1:
        st.markdown("##### Volume et taux par minute")
        st.plotly_chart(fig_timeseries(df), use_container_width=True)
    with g2:
        st.markdown("##### Distribution des scores")
        st.plotly_chart(fig_score_dist(df), use_container_width=True)

    st.markdown("##### Répartition par type de transaction")
    st.plotly_chart(fig_by_type(df), use_container_width=True)

    st.markdown("##### Dernières lignes")
    show_cols = [
        c
        for c in (
            "_ts",
            "transaction_id",
            "transaction_amount_million",
            "transaction_type",
            "merchant_category",
            "fraud_predicted",
            "fraud_score",
        )
        if c in df.columns
    ]
    disp = df[show_cols].tail(200).sort_values("_ts", ascending=False) if not df.empty else df
    st.dataframe(
        disp,
        use_container_width=True,
        height=320,
        column_config={
            "fraud_score": st.column_config.NumberColumn(format="%.4f"),
            "transaction_amount_million": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    csv = df.to_csv(index=False).encode("utf-8") if not df.empty else b""
    st.download_button(
        "Exporter CSV (tampon)",
        data=csv,
        file_name=f"fraud_scored_export_{int(time.time())}.csv",
        mime="text/csv",
        disabled=df.empty,
    )


if __name__ == "__main__":
    main()
