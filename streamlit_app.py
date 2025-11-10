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
N_SIM = 1_000_000
EST = pytz.timezone("US/Eastern")

# --------------------------
# STYLING
# --------------------------
st.markdown("""
    <style>
        body { background-color: #0B132B; color: #E0E1DD; font-family: 'Inter', sans-serif; }
        .title { text-align: center; font-size: 2.8em; font-weight: bold; color: #00C896; margin-bottom: 0.2em; }
        .subtext { text-align: center; color: #9DAAF2; font-size: 1.1em; margin-bottom: 1.5em; }
        .odds-table { background-color: #1C2541; border-radius: 12px; padding: 15px 25px; margin-bottom: 15px; box-shadow: 0 3px 10px rgba(0,0,0,0.3); }
        .odds-table:hover { background-color: #212D52; }
        .team { font-size: 1.1em; color: #F0F0F0; font-weight: 500; }
        .odds-box { text-align: center; background-color: #3A506B; border-radius: 8px; padding: 6px; font-weight: 600; color: #FFFFFF; }
        .game-time { color: #9DAAF2; font-size: 0.9em; text-align: right; }
        .progress-bar { background-color: #2E4057; border-radius: 8px; height: 10px; width: 100%; overflow: hidden; }
        .progress-fill { background-color: #00C896; height: 100%; transition: width 0.5s ease-in-out; }
        .player-img { border-radius: 12px; height: 100px; width: auto; box-shadow: 0 2px 10px rgba(0,0,0,0.4); }
        .scoreboard { background-color: #1C2541; border-radius: 12px; padding: 15px; margin-bottom: 10px; }
        .scoreboard:hover { background-color: #212D52; }
        .category-title { font-size: 1.5em; font-weight: 600; color: #00C896; margin-top: 20px; }
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

PLAYER_IMAGES = {
    "Los Angeles Lakers": "https://cdn.nba.com/headshots/nba/latest/1040x760/2544.png",  # LeBron
    "Golden State Warriors": "https://cdn.nba.com/headshots/nba/latest/1040x760/201939.png",  # Curry
    "Dallas Mavericks": "https://cdn.nba.com/headshots/nba/latest/1040x760/1629029.png",  # Luka
    "Milwaukee Bucks": "https://cdn.nba.com/headshots/nba/latest/1040x760/203507.png",  # Giannis
    "Philadelphia 76ers": "https://cdn.nba.com/headshots/nba/latest/1040x760/203954.png",  # Embiid
}

def logo(team):
    key = TEAM_LOGOS.get(team)
    return f"https://a.espncdn.com/i/teamlogos/nba/500/{key}.png" if key else ""

def player_img(team):
    return PLAYER_IMAGES.get(team, "https://cdn-icons-png.flaticon.com/512/833/833314.png")

def american_to_prob(odds):
    if odds > 0: return 100 / (odds + 100)
    else: return abs(odds) / (abs(odds) + 100)

def monte_carlo_moneyline(home_odds, away_odds):
    home_prob = american_to_prob(home_odds)
    away_prob = american_to_prob(away_odds)
    draws = np.random.rand(N_SIM)
    home_wins = np.sum(draws < home_prob / (home_prob + away_prob))
    conf = home_wins / N_SIM
    return ("Home" if conf >= 0.5 else "Away", round(conf * 100, 2))

def monte_carlo_spread(spread):
    draws = np.random.randn(N_SIM)
    cover_prob = np.mean(draws > (spread / 10.0))
    return ("Home" if cover_prob > 0.5 else "Away", round(cover_prob * 100, 2))

def monte_carlo_total(total):
    draws = np.random.normal(220, 15, N_SIM)
    over_prob = np.mean(draws > total)
    return ("Over" if over_prob > 0.5 else "Under", round(over_prob * 100, 2))

@st.cache_data(ttl=300)
def fetch_live_odds():
    params = {
        "apiKey": ODDS_API_KEY, "regions": "us",
        "markets": "h2h,spreads,totals", "oddsFormat": "american"
    }
    res = requests.get(ODDS_API_URL, params=params)
    return res.json() if res.status_code == 200 else []

def progress_bar(confidence):
    return f"""
        <div class="progress-bar"><div class="progress-fill" style="width:{confidence}%;"></div></div>
        <span style='color:#9DAAF2;font-size:0.9em;'>{confidence}%</span>
    """

# --------------------------
# TABS
# --------------------------
tab1, tab2, tab3 = st.tabs(["🏠 Top Predictions", "🎯 Live Predictions", "📊 Prediction History"])

# ===================== TAB 1: HOME PAGE =====================
with tab1:
    st.markdown(f"<div class='title'>🏀 Top Predictions for {datetime.now(EST).strftime('%m/%d/%Y')}</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtext'>Highest confidence Moneyline, Spread, and Total picks from Monte Carlo AI</div>", unsafe_allow_html=True)

    games = fetch_live_odds()
    top_ml, top_sp, top_tot = [], [], []

    for game in games:
        bookmaker = game["bookmakers"][0]
        home, away = game["home_team"], game["away_team"]
        h2h = next((m for m in bookmaker["markets"] if m["key"] == "h2h"), None)
        spreads = next((m for m in bookmaker["markets"] if m["key"] == "spreads"), None)
        totals = next((m for m in bookmaker["markets"] if m["key"] == "totals"), None)
        if not h2h or not spreads or not totals: continue

        home_odds, away_odds = h2h["outcomes"][0]["price"], h2h["outcomes"][1]["price"]
        spread, total = spreads["outcomes"][0]["point"], totals["outcomes"][0]["point"]
        ml_pred, ml_conf = monte_carlo_moneyline(home_odds, away_odds)
        sp_pred, sp_conf = monte_carlo_spread(spread)
        tot_pred, tot_conf = monte_carlo_total(total)

        top_ml.append((home, away, ml_pred, ml_conf, home_odds, away_odds))
        top_sp.append((home, away, sp_pred, sp_conf, spread))
        top_tot.append((home, away, tot_pred, tot_conf, total))

    def show_top(title, data, metric_label):
        st.markdown(f"<div class='category-title'>{title}</div>", unsafe_allow_html=True)
        for (home, away, pred, conf, *extra) in sorted(data, key=lambda x: x[3], reverse=True)[:3]:
            team = home if pred == "Home" else away
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.image(player_img(team), width=130)
                st.markdown(f"<b>{team}</b><br>{metric_label}: {extra[0]} | Confidence: {conf}%")
            with col2:
                st.image(logo(team), width=60)
            with col3:
                st.markdown(progress_bar(conf), unsafe_allow_html=True)
            st.markdown("---")

    show_top("🏆 Top 3 Moneyline Predictions", top_ml, "Odds")
    show_top("📈 Top 3 Spread Predictions", top_sp, "Spread")
    show_top("🔥 Top 3 Total (O/U) Predictions", top_tot, "Total")

# ===================== TAB 2: LIVE PREDICTIONS =====================
with tab2:
    st.markdown("<div class='title'>🎯 Live Monte Carlo Predictions</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtext'>Simulated 1Mx to project outcomes</div>", unsafe_allow_html=True)
    games = fetch_live_odds()

    for game in games:
        bookmaker = game["bookmakers"][0]
        home = game["home_team"]
        away = game["away_team"]
        utc_time = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))
        est_time = utc_time.astimezone(EST).strftime("%I:%M %p ET")

        h2h = next((m for m in bookmaker["markets"] if m["key"] == "h2h"), None)
        spreads = next((m for m in bookmaker["markets"] if m["key"] == "spreads"), None)
        totals = next((m for m in bookmaker["markets"] if m["key"] == "totals"), None)

        home_odds, away_odds = h2h["outcomes"][0]["price"], h2h["outcomes"][1]["price"]
        spread, total = spreads["outcomes"][0]["point"], totals["outcomes"][0]["point"]

        ml_pred, ml_conf = monte_carlo_moneyline(home_odds, away_odds)
        sp_pred, sp_conf = monte_carlo_spread(spread)
        tot_pred, tot_conf = monte_carlo_total(total)

        st.markdown(f"<div class='odds-table'>", unsafe_allow_html=True)
        col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 2])
        with col1:
            st.markdown(f"<span class='team'><img src='{logo(away)}' width='22'> {away}</span><br>"
                        f"<span class='team'><img src='{logo(home)}' width='22'> {home}</span><br>"
                        f"<div class='game-time'>{est_time}</div>", unsafe_allow_html=True)
        with col2: st.markdown(f"**Spread**<br>+{spread}<br>-{spread}", unsafe_allow_html=True)
        with col3: st.markdown(f"**Moneyline**<br>{away_odds}<br>{home_odds}", unsafe_allow_html=True)
        with col4: st.markdown(f"**Total (O/U)**<br>O {total}<br>U {total}", unsafe_allow_html=True)
        with col5:
            st.markdown(f"🏆 **Winner:** {ml_pred}<br>{progress_bar(ml_conf)}", unsafe_allow_html=True)
            st.markdown(f"📈 **Spread:** {sp_pred}<br>{progress_bar(sp_conf)}", unsafe_allow_html=True)
            st.markdown(f"🔥 **Total:** {tot_pred}<br>{progress_bar(tot_conf)}", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ===================== TAB 3: HISTORY =====================
with tab3:
    st.markdown("<div class='title'>📊 Prediction History</div>", unsafe_allow_html=True)

    with st.expander("📅 Today's Upcoming Predictions"):
        st.markdown("### Tonight's Games & Predictions")
        if os.path.exists(DATA_FILE):
            df = pd.read_csv(DATA_FILE)
            today = datetime.now().strftime("%Y-%m-%d")
            todays = df[df["date"] == today]
            for _, row in todays.iterrows():
                st.markdown(f"<div class='scoreboard'>"
                            f"{row['away_team']} vs {row['home_team']}<br>"
                            f"Moneyline: {row['moneyline_pred']} ({row['moneyline_conf']}%) | "
                            f"Spread: {row['spread_pred']} ({row['spread_conf']}%) | "
                            f"Total: {row['total_pred']} ({row['total_conf']}%)"
                            f"</div>", unsafe_allow_html=True)
        else:
            st.info("No games predicted yet.")

    with st.expander("📜 Historical Predictions"):
        if os.path.exists(DATA_FILE):
            df = pd.read_csv(DATA_FILE)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No historical data available.")
