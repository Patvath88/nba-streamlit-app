import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timezone
import os
import math

# --------------------------
# CONFIG
# --------------------------
st.set_page_config(page_title="🏀 NBA Monte Carlo AI Dashboard", layout="wide")

ODDS_API_KEY = "e11d4159145383afd3a188f99489969e"
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
DATA_FILE = "predictions.csv"
N_SIM = 1_000_000  # Monte Carlo runs

# --------------------------
# CUSTOM STYLING
# --------------------------
st.markdown("""
    <style>
        body {
            background-color: #0B132B;
            color: #E0E1DD;
            font-family: 'Inter', sans-serif;
        }
        .title {
            text-align: center;
            font-size: 2.6em;
            font-weight: bold;
            color: #00C896;
            margin-bottom: 0.2em;
        }
        .subtext {
            text-align: center;
            color: #9DAAF2;
            font-size: 1.1em;
            margin-bottom: 1.5em;
        }
        .card {
            background-color: #1C2541;
            border-radius: 18px;
            padding: 22px;
            margin-bottom: 20px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            transition: transform 0.2s ease-in-out;
        }
        .card:hover { transform: scale(1.015); background-color: #212D52; }
        .team { font-size: 1.2em; font-weight: bold; color: #F0F0F0; }
        .prediction { background-color: #3A506B; border-radius: 12px; padding: 10px; margin-top: 10px; }
        .metric { color: #00FFAE; font-weight: bold; }
        img.logo { width: 40px; vertical-align: middle; margin-right: 8px; }
    </style>
""", unsafe_allow_html=True)

# --------------------------
# HELPERS
# --------------------------
TEAM_LOGOS = {
    "Boston Celtics": "bos", "Brooklyn Nets": "bkn", "New York Knicks": "nyk", "Miami Heat": "mia",
    "Chicago Bulls": "chi", "Cleveland Cavaliers": "cle", "Golden State Warriors": "gsw",
    "Los Angeles Lakers": "lal", "Phoenix Suns": "phx", "Milwaukee Bucks": "mil",
    "Dallas Mavericks": "dal", "Denver Nuggets": "den", "Memphis Grizzlies": "mem",
    "Sacramento Kings": "sac", "San Antonio Spurs": "sas", "Utah Jazz": "uta",
    "Toronto Raptors": "tor", "Philadelphia 76ers": "phi", "Washington Wizards": "was",
    "Houston Rockets": "hou", "Oklahoma City Thunder": "okc", "Minnesota Timberwolves": "min",
    "Atlanta Hawks": "atl", "Detroit Pistons": "det", "Portland Trail Blazers": "por",
    "New Orleans Pelicans": "nop", "Orlando Magic": "orl", "Indiana Pacers": "ind",
    "Los Angeles Clippers": "lac", "Charlotte Hornets": "cha",
}

def logo(team):
    key = TEAM_LOGOS.get(team)
    return f"https://a.espncdn.com/i/teamlogos/nba/500/{key}.png" if key else ""

def american_to_prob(odds):
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def monte_carlo_moneyline(home_odds, away_odds):
    home_prob = american_to_prob(home_odds)
    away_prob = american_to_prob(away_odds)
    draws = np.random.rand(N_SIM)
    home_wins = np.sum(draws < home_prob / (home_prob + away_prob))
    conf = home_wins / N_SIM
    winner = "Home" if conf >= 0.5 else "Away"
    return winner, round(conf * 100, 2)

def monte_carlo_spread(spread):
    draws = np.random.randn(N_SIM)
    cover_prob = np.mean(draws > (spread / 10.0))  # simulated coverage distribution
    team = "Home" if cover_prob > 0.5 else "Away"
    return team, round(cover_prob * 100, 2)

def monte_carlo_total(total):
    draws = np.random.normal(220, 15, N_SIM)
    over_prob = np.mean(draws > total)
    pick = "Over" if over_prob > 0.5 else "Under"
    return pick, round(over_prob * 100, 2)

def fetch_live_odds():
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american"
    }
    res = requests.get(ODDS_API_URL, params=params)
    if res.status_code != 200:
        st.error(f"API error: {res.text}")
        return []
    return res.json()

def save_prediction(data):
    df = pd.DataFrame(data)
    if os.path.exists(DATA_FILE):
        old = pd.read_csv(DATA_FILE)
        df = pd.concat([old, df], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

# --------------------------
# HEADER
# --------------------------
st.markdown("<div class='title'>🏀 NBA Monte Carlo AI Prediction Dashboard</div>", unsafe_allow_html=True)
st.markdown("<div class='subtext'>Simulated 1,000,000x Monte Carlo outcomes | FanDuel-style visualization</div>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🎯 Live Simulated Predictions", "📊 Historical Results"])

# --------------------------
# TAB 1: AUTO MONTE CARLO
# --------------------------
with tab1:
    games = fetch_live_odds()
    if not games:
        st.warning("No NBA games found or API limit reached.")
    else:
        predictions = []
        for game in games:
            bookmaker = game["bookmakers"][0]
            home_team = game["home_team"]
            away_team = game["away_team"]
            commence_time = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00")).astimezone(timezone.utc)
            commence_str = commence_time.strftime("%Y-%m-%d %I:%M %p EST")

            h2h = next((m for m in bookmaker["markets"] if m["key"] == "h2h"), None)
            spreads = next((m for m in bookmaker["markets"] if m["key"] == "spreads"), None)
            totals = next((m for m in bookmaker["markets"] if m["key"] == "totals"), None)

            home_odds = h2h["outcomes"][0]["price"] if h2h else 0
            away_odds = h2h["outcomes"][1]["price"] if h2h else 0
            spread = spreads["outcomes"][0]["point"] if spreads else 0
            total = totals["outcomes"][0]["point"] if totals else 0

            ml_pred, ml_conf = monte_carlo_moneyline(home_odds, away_odds)
            sp_pred, sp_conf = monte_carlo_spread(spread)
            tot_pred, tot_conf = monte_carlo_total(total)

            predictions.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "home_team": home_team,
                "away_team": away_team,
                "moneyline_pred": ml_pred,
                "moneyline_conf": ml_conf,
                "spread_pred": sp_pred,
                "spread_value": spread,
                "spread_conf": sp_conf,
                "total_pred": tot_pred,
                "total_value": total,
                "total_conf": tot_conf
            })

            st.markdown(f"<div class='card'>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='game-header'><img class='logo' src='{logo(away_team)}'> {away_team} 🆚 "
                f"<img class='logo' src='{logo(home_team)}'> {home_team}</div>",
                unsafe_allow_html=True)
            st.write(f"**Tip-off:** {commence_str}")
            st.write(f"**Odds:** {away_team} {away_odds} | {home_team} {home_odds}")
            st.write(f"**Spread:** {spread} | **Total:** {total}")

            st.markdown(f"""
            <div class='prediction'>
                🏆 <b>Moneyline:</b> {ml_pred} | Confidence: {ml_conf}%<br>
                📈 <b>Spread:</b> {spread} {sp_pred} to Cover | Confidence: {sp_conf}%<br>
                🔥 <b>Total (O/U):</b> {tot_pred} {total} | Confidence: {tot_conf}%
            </div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        save_prediction(predictions)

# --------------------------
# TAB 2: HISTORY
# --------------------------
with tab2:
    st.markdown("### 📊 Historical Predictions")
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        st.dataframe(df, use_container_width=True, hide_index=True)
        avg_ml = round(df["moneyline_conf"].mean(), 2)
        avg_sp = round(df["spread_conf"].mean(), 2)
        avg_tot = round(df["total_conf"].mean(), 2)
        col1, col2, col3 = st.columns(3)
        col1.metric("Avg ML Confidence", f"{avg_ml}%")
        col2.metric("Avg Spread Confidence", f"{avg_sp}%")
        col3.metric("Avg Total Confidence", f"{avg_tot}%")
    else:
        st.info("No predictions recorded yet.")
