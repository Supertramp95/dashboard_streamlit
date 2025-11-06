"""Streamlit app per visualizzare gli esiti storici calcolati dal modulo di analisi."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st


BASE_ANALYSIS_PATH = Path("data").resolve()



# ----------------------------------------------------------------------------
# Funzioni di utilità
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame:
    """Carica un CSV in un DataFrame pandas con caching."""

    if not path.exists():
        raise FileNotFoundError(f"CSV non trovato: {path}")

    df = pd.read_csv(path)
    return df


def get_available_leagues(base_path: Path = BASE_ANALYSIS_PATH) -> Dict[str, Path]:
    """Adatta la lettura dei CSV per ambiente GitHub (senza sottocartelle)."""
    leagues: Dict[str, Path] = {}

    # Caso 1: struttura locale (con sottocartelle)
    subfolders = [f for f in base_path.iterdir() if f.is_dir()]
    if subfolders:
        for child in sorted(subfolders):
            leagues[child.name] = child
        return leagues

    # Caso 2: ambiente GitHub (solo file diretti)
    csv_files = list(base_path.glob("*.csv"))
    if csv_files:
        leagues["default"] = base_path

    return leagues



def format_percentage_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Formatta le colonne percentuali a due decimali (senza conversione stringa)."""

    pct_cols = [col for col in df.columns if col.endswith("_percentage")]
    df_formatted = df.copy()
    for col in pct_cols:
        df_formatted[col] = df_formatted[col].astype(float).round(2)

    return df_formatted


def render_table(df: pd.DataFrame, selected_outcomes: List[str]) -> None:
    """Mostra il DataFrame con formattazione Streamlit."""

    if df.empty:
        st.info("Nessun dato disponibile per la selezione corrente.")
        return

    df_display = format_percentage_columns(df)

    highlight_cols = [f"{outcome}_percentage" for outcome in selected_outcomes]

    def highlight_max(s: pd.Series) -> List[str]:
        if s.name in highlight_cols:
            is_max = s == s.max()
            return ["background-color: #c8e6c9; font-weight: bold" if val else "" for val in is_max]
        return ["" for _ in s]

    styled = df_display.style.apply(highlight_max, axis=0)
    st.dataframe(styled, use_container_width=True)


def compute_summary_metrics(df: pd.DataFrame, selected_outcomes: List[str]) -> Optional[pd.Series]:
    """Calcola media percentuali degli esiti selezionati."""

    if df.empty:
        return None

    summaries = {}
    for outcome in selected_outcomes:
        col = f"{outcome}_percentage"
        if col in df.columns:
            summaries[outcome] = df[col].mean()

    return pd.Series(summaries).round(2) if summaries else None


# ----------------------------------------------------------------------------
# Configurazione pagina
# ----------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="Football AI 2.0 – Analisi Esiti Storici")
st.title("📊 Football AI 2.0 – Analisi Esiti Storici")


# ----------------------------------------------------------------------------
# Sidebar: selezioni utente
# ----------------------------------------------------------------------------
st.sidebar.header("Controlli")
available_leagues = get_available_leagues()

if not available_leagues:
    st.sidebar.warning("Nessuna lega trovata nella cartella di analisi. Esegui il modulo prima di aprire la dashboard.")
    st.stop()

selected_leagues = st.sidebar.multiselect(
    "Seleziona leghe/coppe",
    list(available_leagues.keys()),
    default=list(available_leagues.keys())[:1],
)

analysis_type = st.sidebar.radio("Tipo di analisi", ("Stagione", "Giornata"))

selected_outcomes = st.sidebar.multiselect(
    "Esiti da visualizzare",
    ["over_25", "gg", "multigol_2_4", "combo_multigol_ht0_2_ft1_3"],
    default=["over_25", "gg"],
)

if not selected_leagues:
    st.info("Seleziona almeno una lega/coppa dalla sidebar per continuare.")
    st.stop()

if not selected_outcomes:
    st.info("Seleziona almeno un esito dalla sidebar per continuare.")
    st.stop()


# ----------------------------------------------------------------------------
# Caricamento dati in base alla selezione
# ----------------------------------------------------------------------------
analysis_file = "analisi_stagioni.csv" if analysis_type == "Stagione" else "analisi_giornate.csv"
dfs = []

for league in selected_leagues:
    league_path = available_leagues[league]
    csv_path = league_path / analysis_file
    try:
        df = load_csv(csv_path)
    except FileNotFoundError:
        st.warning(f"File '{analysis_file}' non trovato per la lega {league}.")
        continue

    df["league"] = league
    dfs.append(df)

if not dfs:
    st.error("Nessun dato disponibile con le selezioni effettuate.")
    st.stop()

data = pd.concat(dfs, ignore_index=True)

# Ordina colonne principali
id_cols = ["league"]
if analysis_type == "Stagione":
    id_cols.append("season")
else:
    id_cols.extend(["season", "round"])

order_cols = id_cols + [f"{outcome}_count" for outcome in selected_outcomes] + [
    f"{outcome}_percentage" for outcome in selected_outcomes
]

available_cols = [col for col in order_cols if col in data.columns]
extra_cols = [col for col in data.columns if col not in available_cols]
data = data[available_cols + extra_cols]

st.subheader(f"Risultati – Analisi per {analysis_type.lower()}")
render_table(data, selected_outcomes)


# ----------------------------------------------------------------------------
# Statistiche riassuntive
# ----------------------------------------------------------------------------
st.markdown("---")
total_matches = data["total_matches"].sum() if "total_matches" in data.columns else None

summary = compute_summary_metrics(data, selected_outcomes)

cols = st.columns(2)
with cols[0]:
    if total_matches is not None:
        st.metric("Partite analizzate", f"{int(total_matches):,}".replace(",", "."))
    else:
        st.metric("Partite analizzate", "Dato non disponibile")

with cols[1]:
    if summary is not None:
        st.write("**Media percentuali esiti selezionati:**")
        for outcome, value in summary.items():
            st.write(f"- {outcome.replace('_', ' ').title()}: {value:.2f}%")
    else:
        st.write("Nessuna media calcolabile per gli esiti selezionati.")




