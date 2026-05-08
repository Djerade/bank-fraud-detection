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

FRAGMENT_INTERVAL_S = 2.0
ALERT_THRESHOLD = 0.7


def _env(name: str, default: str) -> str:
    v = os.environ.get(name, "").strip()
    return v if v else default


def inject_style() -> None:
    st.markdown(
        """
        <style>
          .main-header {
            font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em;
            color: #f8fafc; margin-bottom: 0.15rem;
          }
          .sub-header {
            font-size: 0.95rem; color: #94a3b8; margin-bottom: 1.25rem;
          }
          div[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
          .rt-count-wrap {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0b1220 100%);
            border: 1px solid #334155; border-radius: 16px;
            padding: 1.25rem 1.5rem 1.1rem 1.5rem; margin-bottom: 1rem;
          }
          .rt-count-big {
            font-size: clamp(2.5rem, 6vw, 3.75rem); font-weight: 800;
            line-height: 1.05; letter-spacing: -0.03em; color: #38bdf8;
            font-variant-numeric: tabular-nums;
          }
          .rt-count-label { font-size: 0.95rem; color: #94a3b8; margin-top: 0.35rem; }
          .rt-count-meta  { font-size: 0.8rem;  color: #64748b; margin-top: 0.5rem;  }
          .alert-badge {
            background: #450a0a; border: 1px solid #ef4444; border-radius: 8px;
            padding: 0.15rem 0.55rem; font-size: 0.78rem; color: #fca5a5;
            font-weight: 600;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── Helpers ──────────────────────────────────────────────────────────────────

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
        df["fraud_predicted"] = (
            pd.to_numeric(df["fraud_predicted"], errors="coerce").fillna(0).astype(int)
        )
    if "transaction_amount_million" in df.columns:
        df["transaction_amount_million"] = pd.to_numeric(
            df["transaction_amount_million"], errors="coerce"
        )
    return df


def empty_chart(message: str, height: int = 320) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a",
        margin=dict(l=48, r=24, t=32, b=32), height=height,
        annotations=[dict(
            text=message, xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=14, color="#64748b"),
        )],
    )
    return fig


_LAYOUT = dict(
    template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a",
    margin=dict(l=48, r=24, t=32, b=48),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)


# ── Graphiques ───────────────────────────────────────────────────────────────

def fig_timeseries(df: pd.DataFrame) -> go.Figure:
    if df.empty or "_ts" not in df.columns:
        return empty_chart("En attente de données…", 380)
    d = df.sort_values("_ts").copy()
    d["minute"] = d["_ts"].dt.floor("min")
    g = d.groupby("minute", as_index=False).agg(n=("_ts", "count"), frauds=("fraud_predicted", "sum"))
    g["rate_pct"] = (g["frauds"] / g["n"].clip(lower=1) * 100.0).round(2)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=g["minute"], y=g["n"], name="Volume / min", marker_color="#334155"), secondary_y=False)
    fig.add_trace(go.Scatter(x=g["minute"], y=g["rate_pct"], name="% alertes",
        mode="lines+markers", line=dict(color="#f97316", width=2), marker=dict(size=5)), secondary_y=True)
    fig.update_yaxes(title_text="Transactions", secondary_y=False, gridcolor="#1e293b")
    fig.update_yaxes(title_text="% détecté", secondary_y=True, range=[0, 105], gridcolor="#1e293b")
    fig.update_xaxes(gridcolor="#1e293b")
    fig.update_layout(**_LAYOUT, height=380)
    return fig


def fig_score_dist(df: pd.DataFrame) -> go.Figure:
    if df.empty or "fraud_score" not in df.columns or df["fraud_score"].dropna().empty:
        return empty_chart("Pas encore de scores.", 340)
    sub = df.dropna(subset=["fraud_score"])
    color_col = "fraud_predicted" if "fraud_predicted" in sub.columns else None
    if color_col:
        fig = px.histogram(sub, x="fraud_score", color=color_col, nbins=40,
            color_discrete_map={0: "#38bdf8", 1: "#fb7185"},
            labels={"fraud_score": "Score fraude", "count": "Effectif"})
    else:
        fig = px.histogram(sub, x="fraud_score", nbins=40,
            labels={"fraud_score": "Score fraude", "count": "Effectif"})
    fig.add_vline(x=ALERT_THRESHOLD, line_dash="dash", line_color="#f97316",
        annotation_text=f"Seuil {ALERT_THRESHOLD}", annotation_position="top right")
    fig.update_layout(**_LAYOUT, bargap=0.08, height=340, legend_title_text="Fraude prédite")
    return fig


def fig_by_type(df: pd.DataFrame) -> go.Figure:
    if df.empty or "transaction_type" not in df.columns:
        return empty_chart("Type de transaction manquant.", 300)
    g = (df.groupby("transaction_type", as_index=False)
         .agg(volume=("transaction_type", "count"), frauds=("fraud_predicted", "sum"))
         .sort_values("volume", ascending=False))
    g["ok"] = g["volume"] - g["frauds"]
    fig = go.Figure(data=[
        go.Bar(name="Légitime", x=g["transaction_type"], y=g["ok"], marker_color="#22c55e"),
        go.Bar(name="Alerte",   x=g["transaction_type"], y=g["frauds"], marker_color="#ef4444"),
    ])
    fig.update_layout(**_LAYOUT, barmode="stack", height=300,
        yaxis=dict(gridcolor="#1e293b"), xaxis=dict(gridcolor="#1e293b"))
    return fig


def fig_by_merchant(df: pd.DataFrame) -> go.Figure:
    if df.empty or "merchant_category" not in df.columns:
        return empty_chart("Catégorie marchande manquante.", 300)
    g = (df.groupby("merchant_category", as_index=False)
         .agg(volume=("merchant_category", "count"), frauds=("fraud_predicted", "sum"))
         .sort_values("frauds", ascending=True))
    g["rate"] = (g["frauds"] / g["volume"].clip(lower=1) * 100).round(1)
    fig = go.Figure(data=[
        go.Bar(name="Légitime", y=g["merchant_category"], x=g["volume"] - g["frauds"],
               orientation="h", marker_color="#0ea5e9"),
        go.Bar(name="Alerte",   y=g["merchant_category"], x=g["frauds"],
               orientation="h", marker_color="#ef4444",
               text=[f"{r:.0f}%" for r in g["rate"]], textposition="outside"),
    ])
    fig.update_layout(**_LAYOUT, barmode="stack", height=300,
        xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"))
    return fig


def fig_by_location(df: pd.DataFrame) -> go.Figure:
    if df.empty or "transaction_location" not in df.columns:
        return empty_chart("Localisation manquante.", 340)
    g = (df.groupby("transaction_location", as_index=False)
         .agg(volume=("transaction_location", "count"), frauds=("fraud_predicted", "sum"))
         .sort_values("frauds", ascending=False).head(12))
    g["rate"] = (g["frauds"] / g["volume"].clip(lower=1) * 100).round(1)
    fig = px.bar(g, x="transaction_location", y="frauds", color="rate",
        color_continuous_scale="Reds",
        labels={"transaction_location": "Localisation", "frauds": "Alertes", "rate": "Taux %"},
        text="frauds")
    fig.update_traces(textposition="outside")
    fig.update_layout(**_LAYOUT, height=340, coloraxis_colorbar=dict(title="Taux %"),
        xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"))
    return fig


def fig_by_card(df: pd.DataFrame) -> go.Figure:
    if df.empty or "card_type" not in df.columns:
        return empty_chart("Type de carte manquant.", 300)
    g = df.groupby(["card_type", "fraud_predicted"], as_index=False).size()
    g.columns = ["card_type", "fraud_predicted", "count"]
    fig = px.bar(g, x="card_type", y="count", color="fraud_predicted",
        color_discrete_map={0: "#22c55e", 1: "#ef4444"},
        labels={"card_type": "Carte", "count": "Transactions", "fraud_predicted": "Fraude"},
        barmode="group")
    fig.update_layout(**_LAYOUT, height=300,
        yaxis=dict(gridcolor="#1e293b"), xaxis=dict(gridcolor="#1e293b"),
        legend_title_text="Fraude prédite")
    return fig


def fig_amount_dist(df: pd.DataFrame) -> go.Figure:
    if df.empty or "transaction_amount_million" not in df.columns:
        return empty_chart("Montants manquants.", 300)
    sub = df.dropna(subset=["transaction_amount_million"])
    if sub.empty:
        return empty_chart("Montants manquants.", 300)
    fig = px.box(sub, x="fraud_predicted" if "fraud_predicted" in sub.columns else None,
        y="transaction_amount_million",
        color="fraud_predicted" if "fraud_predicted" in sub.columns else None,
        color_discrete_map={0: "#38bdf8", 1: "#fb7185"},
        labels={"transaction_amount_million": "Montant (M)", "fraud_predicted": "Fraude"},
        points=False)
    fig.update_layout(**_LAYOUT, height=300,
        yaxis=dict(gridcolor="#1e293b"), xaxis=dict(gridcolor="#1e293b"),
        legend_title_text="Fraude prédite")
    return fig


# ── Polling ──────────────────────────────────────────────────────────────────

def live_poll(demo: bool, bootstrap: str, topic: str, group_id: str, rng_batch: int) -> None:
    buf: deque = st.session_state["rows"]
    n_before = len(buf)
    if demo:
        for row in demo_batch(rng_batch):
            buf.append(row)
        st.session_state["kafka_error"] = None
    else:
        try:
            cons = kafka_consumer_resource(bootstrap, topic, group_id)
            for row in poll_records(cons, max_messages=1000):
                buf.append(row)
            st.session_state["kafka_error"] = None
        except Exception as e:
            st.session_state["kafka_error"] = str(e)
    added = len(buf) - n_before
    st.session_state["last_poll_added"] = int(added)
    st.session_state["total_ingested"] = int(st.session_state.get("total_ingested", 0)) + int(added)
    st.session_state["last_poll_ts"] = time.time()


def _defaults() -> None:
    for key, default in [
        ("rows", deque()),
        ("kafka_error", None),
        ("dash_demo", False),
        ("dash_bootstrap", _env("KAFKA_BOOTSTRAP_SERVERS", BOOTSTRAP_SERVERS)),
        ("dash_topic", _env("KAFKA_TOPIC_SCORED", TOPIC_SCORED)),
        ("dash_group", _env("DASHBOARD_KAFKA_GROUP", "fraud-dashboard-ui")),
        ("dash_demo_n", 6),
        ("total_ingested", 0),
        ("last_poll_added", 0),
        ("last_poll_ts", None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default


# ── Fragment principal (re-rendu toutes les 2 s) ──────────────────────────────

@st.fragment(run_every=timedelta(seconds=FRAGMENT_INTERVAL_S))
def poll_fragment() -> None:
    live_poll(
        bool(st.session_state.get("dash_demo")),
        str(st.session_state.get("dash_bootstrap", BOOTSTRAP_SERVERS)),
        str(st.session_state.get("dash_topic", TOPIC_SCORED)),
        str(st.session_state.get("dash_group", "fraud-dashboard-ui")),
        int(st.session_state.get("dash_demo_n", 6)),
    )

    err = st.session_state.get("kafka_error")
    if err and not st.session_state.get("dash_demo"):
        st.warning(f"Kafka : {err}")

    rows = list(st.session_state["rows"])
    df = buffer_to_dataframe(rows)

    total_rx  = int(st.session_state.get("total_ingested", 0))
    last_add  = int(st.session_state.get("last_poll_added", 0))
    last_ts   = st.session_state.get("last_poll_ts")
    ts_txt    = time.strftime("%H:%M:%S", time.localtime(last_ts)) if isinstance(last_ts, (int, float)) else "—"

    # ── Compteur principal ────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="rt-count-wrap">
          <div class="rt-count-big">{total_rx:,}</div>
          <div class="rt-count-label">Transactions reçues depuis le démarrage du topic (historique complet)</div>
          <div class="rt-count-meta">+{last_add} ce cycle · dernier poll : {ts_txt} · rafraîchissement ~{FRAGMENT_INTERVAL_S:.0f} s</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Métriques ─────────────────────────────────────────────────────────────
    n      = len(df)
    frauds = int(df["fraud_predicted"].sum()) if n and "fraud_predicted" in df.columns else 0
    rate   = frauds / n * 100.0 if n else 0.0

    avg_score = 0.0
    if n and "fraud_score" in df.columns and "fraud_predicted" in df.columns:
        m = df.loc[df["fraud_predicted"] == 1, "fraud_score"].mean()
        avg_score = float(m) if pd.notna(m) else 0.0

    avg_amount = 0.0
    if n and "transaction_amount_million" in df.columns:
        avg_amount = float(df["transaction_amount_million"].mean()) if not df["transaction_amount_million"].isna().all() else 0.0

    critical = int((df["fraud_score"] >= ALERT_THRESHOLD).sum()) if n and "fraud_score" in df.columns else 0
    unique_clients = int(df["customer_id"].nunique()) if "customer_id" in df.columns else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Transactions",        f"{n:,}".replace(",", " "))
    c2.metric("Alertes fraude",      f"{frauds:,}".replace(",", " "))
    c3.metric("Taux d'alerte",       f"{rate:.2f} %")
    c4.metric(f"Critiques (≥ {ALERT_THRESHOLD})", f"{critical:,}".replace(",", " "))
    c5.metric("Montant moyen (M)",   f"{avg_amount:.2f}")
    c6.metric("Clients uniques",     f"{unique_clients:,}".replace(",", " "))

    st.divider()

    # ── Ligne 1 : Volume + scores ─────────────────────────────────────────────
    col_l, col_r = st.columns([1.3, 0.7])
    with col_l:
        st.markdown("##### Volume et taux d'alerte par minute")
        st.plotly_chart(fig_timeseries(df), use_container_width=True)
    with col_r:
        st.markdown("##### Distribution des scores de fraude")
        st.plotly_chart(fig_score_dist(df), use_container_width=True)

    st.divider()

    # ── Ligne 2 : Par type et par marchand ────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("##### Répartition par type de transaction")
        st.plotly_chart(fig_by_type(df), use_container_width=True)
    with col_b:
        st.markdown("##### Répartition par catégorie marchande")
        st.plotly_chart(fig_by_merchant(df), use_container_width=True)

    st.divider()

    # ── Ligne 3 : Localisation + Carte + Montants ────────────────────────────
    col_p, col_q, col_r2 = st.columns([1.4, 0.8, 0.8])
    with col_p:
        st.markdown("##### Alertes par localisation (top 12)")
        st.plotly_chart(fig_by_location(df), use_container_width=True)
    with col_q:
        st.markdown("##### Fraude par type de carte")
        st.plotly_chart(fig_by_card(df), use_container_width=True)
    with col_r2:
        st.markdown("##### Distribution montants (Normal vs Fraude)")
        st.plotly_chart(fig_amount_dist(df), use_container_width=True)

    st.divider()

    # ── Alertes critiques ─────────────────────────────────────────────────────
    if n and "fraud_score" in df.columns:
        critical_df = df[df["fraud_score"] >= ALERT_THRESHOLD].copy()
        st.markdown(
            f"##### Alertes critiques (score ≥ {ALERT_THRESHOLD}) "
            f"<span class='alert-badge'>{len(critical_df):,} alertes</span>",
            unsafe_allow_html=True,
        )
        if not critical_df.empty:
            alert_cols = [c for c in ("_ts", "transaction_id", "customer_id",
                "transaction_amount_million", "transaction_type", "merchant_category",
                "transaction_location", "card_type", "fraud_score") if c in critical_df.columns]
            disp_alerts = (
                critical_df[alert_cols]
                .sort_values("fraud_score", ascending=False)
                .head(100)
            )
            st.dataframe(
                disp_alerts, use_container_width=True, height=280,
                column_config={
                    "fraud_score": st.column_config.ProgressColumn(
                        "Score fraude", min_value=0.0, max_value=1.0, format="%.4f"
                    ),
                    "transaction_amount_million": st.column_config.NumberColumn(format="%.2f M"),
                },
            )
        else:
            st.info("Aucune alerte critique pour l'instant.")

    st.divider()

    # ── Toutes les transactions ───────────────────────────────────────────────
    st.markdown("##### Toutes les transactions (les 500 plus récentes)")
    all_cols = [c for c in ("_ts", "transaction_id", "customer_id",
        "transaction_amount_million", "transaction_type", "merchant_category",
        "transaction_location", "card_type", "fraud_predicted", "fraud_score")
        if c in df.columns]
    disp_all = df[all_cols].tail(500).sort_values("_ts", ascending=False) if not df.empty else df
    st.dataframe(
        disp_all, use_container_width=True, height=340,
        column_config={
            "fraud_score": st.column_config.NumberColumn(format="%.4f"),
            "transaction_amount_million": st.column_config.NumberColumn(format="%.2f M"),
            "fraud_predicted": st.column_config.CheckboxColumn("Fraude"),
        },
    )

    # ── Export ────────────────────────────────────────────────────────────────
    csv = df.to_csv(index=False).encode("utf-8") if not df.empty else b""
    st.download_button(
        "Exporter toutes les transactions (CSV)",
        data=csv,
        file_name=f"fraud_scored_{int(time.time())}.csv",
        mime="text/csv",
        disabled=df.empty,
    )


# ── Point d'entrée ────────────────────────────────────────────────────────────

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
        '<p class="sub-header">Surveillance temps réel · topic Kafka scoré · historique complet</p>',
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### Connexion Kafka")
        st.toggle("Mode démo (sans Kafka)", key="dash_demo")
        st.text_input("Bootstrap Kafka", key="dash_bootstrap")
        st.text_input("Topic scoré", key="dash_topic")
        st.text_input("Groupe consommateur", key="dash_group")
        st.slider("Transactions démo / cycle", 1, 20, key="dash_demo_n")
        st.divider()
        st.markdown("### Paramètres")
        st.caption(
            f"Rafraîchissement : {FRAGMENT_INTERVAL_S:.0f} s · "
            f"Seuil alerte critique : {ALERT_THRESHOLD}"
        )
        st.caption("L'historique complet est chargé depuis Kafka au démarrage (`earliest`).")

    poll_fragment()


if __name__ == "__main__":
    main()
