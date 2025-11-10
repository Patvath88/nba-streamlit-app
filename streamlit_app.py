import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timezone, timedelta
import pytz
import os

# --------------------------
# CONFIG
# --------------------------
st.set_page_config(page_title="🏀 NBA Monte Carlo AI Dashboard", layout="wide")

ODDS_API_KEY = "e11d4159145383afd3a188f99489969e"
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
DATA_FILE = "predictions.csv"
N_SIM = 1_000_000  # Monte Carlo simulations
EST = pytz.timezone("US/Eastern")

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
            font-size: 2.5em;
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
        .odds-table {
            background-color: #1C2541;
            border-radius: 12px;
            padding: 15px 25px;
            margin-bottom: 15px;
            transition: all 0.2s ease-in-out;
            box-shadow: 0 3px 10px rgba(0,0,0,0.3);
        }
        .odds-table:hover {
            background-color: #212D52;
        }
        .team {
            font-size: 1.1em;
            color: #F0F0F0;
            font-weight: 500;
        }
        .odds-box {
            text-align: center;
            background-color: #3A506B;
            border-radius: 8px;
            padding: 6px;
            font-weight: 600;
            color: #FFFFFF;
        }
        .game-time {
            color: #9DAAF2;
            font-size: 0.9em;
            text-align: right;
        }
        .progress-bar {
            background-color: #2E4057;
            border-radius: 8px;
            height: 10px;
            width: 100%;
            overflow: hidden;
        }
        .progress-fill {
            background-color: #00C896;
            height: 100%;
            transition: width 0.5s ease-in-out;
        }
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
    cover_prob = np.mean(draws > (spread / 10.0))
    team = "Home" if cover_prob > 0.5 else "Away"
    return team, round(cover_prob * 100, 2)

def monte_carlo_total(total):
    draws = np.random.normal(220, 15, N_SIM)
    over_prob = np.mean(draws > total)
    pick = "Over" if over_prob > 0.5 else "Under"
    return pick, round(over_prob * 100, 2)

@st.cache_data(ttl=300)
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

def progress_bar(confidence):
    return f"""
        <div class="progress-bar"><div class="progress-fill" style="width:{confidence}%;"></div></div>
        <span style='color:#9DAAF2;font-size:0.9em;'>{confidence}% confidence</span>
    """

# --------------------------
# HEADER
# --------------------------
st.markdown("<div class='title'>🏀 NBA Monte Carlo AI Dashboard</div>", unsafe_allow_html=True)
st.markdown("<div class='subtext'>Simulated 1,000,000x Monte Carlo outcomes | Real-time odds in EST</div>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🎯 Live AI Predictions", "📊 History"])

# --------------------------
# TAB 1
# --------------------------
with tab1:
    games = fetch_live_odds()
    if not games:
        st.warning("No NBA games found or API limit reached.")
    else:
        for game in games:
            bookmaker = game["bookmakers"][0]
            home_team = game["home_team"]
            away_team = game["away_team"]
            utc_time = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))
            est_time = utc_time.astimezone(EST)
            est_time_str = est_time.strftime("%I:%M %p ET")

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

            # UI layout in columns
            st.markdown(f"<div class='odds-table'>", unsafe_allow_html=True)
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 2])

            with col1:
                st.markdown(f"<span class='team'><img src='{logo(away_team)}' width='22'> {away_team}</span>", unsafe_allow_html=True)
                st.markdown(f"<span class='team'><img src='{logo(home_team)}' width='22'> {home_team}</span>", unsafe_allow_html=True)
                st.markdown(f"<div class='game-time'>{est_time_str}</div>", unsafe_allow_html=True)

            with col2:
                st.markdown(f"**Spread**<br>+{spread}<br>-{spread}", unsafe_allow_html=True)

            with col3:
                st.markdown(f"**Moneyline**<br>{away_odds}<br>{home_odds}", unsafe_allow_html=True)

            with col4:
                st.markdown(f"**Total (O/U)**<br>O {total}<br>U {total}", unsafe_allow_html=True)

            with col5:
                st.markdown(f"🏆 **Predicted:** {ml_pred}<br>{progress_bar(ml_conf)}", unsafe_allow_html=True)
                st.markdown(f"📈 **Spread:** {sp_pred}<br>{progress_bar(sp_conf)}", unsafe_allow_html=True)
                st.markdown(f"🔥 **Total:** {tot_pred}<br>{progress_bar(tot_conf)}", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

# --------------------------
# TAB 2
# --------------------------
with tab2:
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No predictions stored yet.")
