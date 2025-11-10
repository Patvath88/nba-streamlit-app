import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timezone
import pytz
import os
import random

# --------------------------
# CONFIG
# --------------------------
st.set_page_config(page_title="🏀 Pat's Picks NBA Dashboard", layout="wide")
ODDS_API_KEY = "e11d4159145383afd3a188f99489969e"
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
DATA_FILE = "predictions.csv"
N_SIM = 1_000_000
EST = pytz.timezone("US/Eastern")

# --------------------------
# CUSTOM STYLING
# --------------------------
st.markdown("""
    <style>
        body { background-color: #0B132B; color: #E0E1DD; font-family: 'Inter', sans-serif; }
        .title { text-align: center; font-size: 2.8em; font-weight: bold; color: #00C896; margin-bottom: 0.2em; }
        .subtext { text-align: center; color: #9DAAF2; font-size: 1.1em; margin-bottom: 1.5em; }
        .odds-table { background-color: #1C2541; border-radius: 12px; padding: 15px 25px; margin-bottom: 15px; box-shadow: 0 3px 10px rgba(0,0,0,0.3); }
        .team { font-size: 1.1em; color: #F0F0F0; font-weight: 500; }
        .game-time { color: #9DAAF2; font-size: 0.9em; text-align: right; }
        .progress-bar { background-color: #2E4057; border-radius: 8px; height: 10px; width: 100%; overflow: hidden; }
        .progress-fill { background-color: #00C896; height: 100%; transition: width 0.5s ease-in-out; }
        .category-title { font-size: 1.5em; font-weight: 600; color: #00C896; margin-top: 20px; }
        .player-img { border-radius: 12px; height: 110px; width: auto; box-shadow: 0 2px 10px rgba(0,0,0,0.4); }
        .gold-glow { animation: shimmer 2s infinite linear; background: linear-gradient(90deg, #FFD700, #fff6a1, #FFD700); -webkit-background-clip: text; color: transparent; }
        @keyframes shimmer { 0% { background-position: -200px 0; } 100% { background-position: 200px 0; } }
        .scoreboard { background-color: #1C2541; border-radius: 12px; padding: 15px; margin-bottom: 10px; }
        .scoreboard:hover { background-color: #212D52; }
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
    "Los Angeles Lakers": "https://cdn.nba.com/headshots/nba/latest/1040x760/2544.png",
    "Golden State Warriors": "https://cdn.nba.com/headshots/nba/latest/1040x760/201939.png",
    "Dallas Mavericks": "https://cdn.nba.com/headshots/nba/latest/1040x760/1629029.png",
    "Milwaukee Bucks": "https://cdn.nba.com/headshots/nba/latest/1040x760/203507.png",
    "Philadelphia 76ers": "https://cdn.nba.com/headshots/nba/latest/1040x760/203954.png",
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
tab1, tab2, tab3, tab4 = st.tabs(["🏠 Top Predictions", "🎯 Daily NBA Predictions", "📊 Prediction History", "✅ Recent Wins"])

# ===================== TAB 1: TOP PREDICTIONS =====================
with tab1:
    # === AI Prediction Summary Banner ===
    st.markdown("""
        <style>
        .summary-banner {
            background: linear-gradient(90deg, #004AAD, #002B5B);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            color: white;
            margin-bottom: 30px;
            box-shadow: 0px 4px 15px rgba(0,0,0,0.4);
        }
        .summary-item {
            display: inline-block;
            margin: 0 40px;
            font-size: 1.2em;
            text-align: center;
        }
        .summary-item h3 {
            font-size: 2.3em;
            color: #00FFAE;
            margin: 5px 0;
        }
        .summary-item p {
            font-size: 1.1em;
            color: #BFD7ED;
            margin: 0;
        }
        .summary-logo {
            width: 45px;
            vertical-align: middle;
            margin-left: 8px;
        }
        .sportsbook-badge {
            background: #00C896;
            color: #002B5B;
            padding: 6px 12px;
            border-radius: 8px;
            font-weight: 600;
            display: inline-block;
            margin-top: 8px;
            text-transform: capitalize;
        }
        </style>
    """, unsafe_allow_html=True)

    # Title
    st.markdown(f"<div class='title'>🏀 Top Predictions for {datetime.now(EST).strftime('%m/%d/%Y')}</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtext'>Best AI Monte Carlo picks with sportsbook logos & rankings</div>", unsafe_allow_html=True)

    # Fetch odds data
    games = fetch_live_odds()
    top_ml, top_sp, top_tot = [], [], []

    sportsbook_logos = {
        "fanduel": "https://upload.wikimedia.org/wikipedia/commons/2/27/FanDuel_logo.svg",
        "draftkings": "https://upload.wikimedia.org/wikipedia/commons/a/ae/DraftKings_logo.svg",
        "mgm": "https://upload.wikimedia.org/wikipedia/en/e/e0/BetMGM_logo.svg",
        "caesars": "https://upload.wikimedia.org/wikipedia/commons/8/87/Caesars_Sportsbook_logo.svg",
    }
    sportsbook_names = list(sportsbook_logos.keys())

    # Run Monte Carlo predictions
    for game in games:
        bookmaker = game["bookmakers"][0]
        home, away = game["home_team"], game["away_team"]
        h2h = next((m for m in bookmaker["markets"] if m["key"] == "h2h"), None)
        spreads = next((m for m in bookmaker["markets"] if m["key"] == "spreads"), None)
        totals = next((m for m in bookmaker["markets"] if m["key"] == "totals"), None)
        if not h2h or not spreads or not totals:
            continue

        home_odds, away_odds = h2h["outcomes"][0]["price"], h2h["outcomes"][1]["price"]
        spread, total = spreads["outcomes"][0]["point"], totals["outcomes"][0]["point"]

        # Monte Carlo Simulation for Moneyline
        home_prob = american_to_prob(home_odds)
        away_prob = american_to_prob(away_odds)
        draws = np.random.rand(N_SIM)
        home_wins = np.sum(draws < home_prob / (home_prob + away_prob))
        ml_conf = round((home_wins / N_SIM) * 100, 2)
        ml_pred = "Home" if ml_conf >= 50 else "Away"

        sp_pred, sp_conf = monte_carlo_spread(spread)
        tot_pred, tot_conf = monte_carlo_total(total)

        top_ml.append((home, away, ml_pred, ml_conf, home_odds, away_odds, random.choice(sportsbook_names), home_wins))
        top_sp.append((home, away, sp_pred, sp_conf, spread, random.choice(sportsbook_names), int(N_SIM * sp_conf / 100)))
        top_tot.append((home, away, tot_pred, tot_conf, total, random.choice(sportsbook_names), int(N_SIM * tot_conf / 100)))

    # === Summary Data ===
    total_games = len(games)
    avg_conf = round(np.mean([x[3] for x in top_ml + top_sp + top_tot]) if (top_ml or top_sp or top_tot) else 0, 2)
    best_overall = max(top_ml + top_sp + top_tot, key=lambda x: x[3]) if (top_ml or top_sp or top_tot) else None

    if best_overall:
        best_team = best_overall[0] if best_overall[2] == "Home" else best_overall[1]
        best_conf = best_overall[3]
        best_logo = logo(best_team)
        st.markdown(f"""
            <div class='summary-banner'>
                <div class='summary-item'>
                    <h3>{total_games}</h3>
                    <p>Games Predicted</p>
                </div>
                <div class='summary-item'>
                    <h3>{avg_conf}%</h3>
                    <p>Average Confidence</p>
                </div>
                <div class='summary-item'>
                    <h3>{best_team} <img src='{best_logo}' class='summary-logo'></h3>
                    <p>Top Pick ({best_conf}% Confidence)</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # === Safe Image Handler ===
    def safe_image(url, width, fallback_text="🏀", sportsbook_name=None):
        """
        Renders valid images safely; falls back to placeholders or sportsbook name badges.
        """
        if not url or str(url).strip() in ["", "0", "None"]:
            if sportsbook_name:
                st.markdown(
                    f"<div class='sportsbook-badge'>{sportsbook_name}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div style='width:{width}px;height:{width}px;
                    display:flex;align-items:center;justify-content:center;
                    background:#1C2541;color:#00FFAE;font-size:{width//2}px;
                    border-radius:50%;box-shadow:0 0 10px rgba(0,0,0,0.4);'>
                    {fallback_text}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            return
        try:
            st.image(url, width=width)
        except Exception:
            st.markdown(
                f"""
                <div style='width:{width}px;height:{width}px;
                display:flex;align-items:center;justify-content:center;
                background:#1C2541;color:#00FFAE;font-size:{width//2}px;
                border-radius:50%;box-shadow:0 0 10px rgba(0,0,0,0.4);'>
                {fallback_text}
                </div>
                """,
                unsafe_allow_html=True
            )

    # === Display Top Predictions ===
    def show_top(title, data, metric_label):
        st.markdown(f"<div class='category-title'>{title}</div>", unsafe_allow_html=True)
        for i, (home, away, pred, conf, *extra) in enumerate(sorted(data, key=lambda x: x[3], reverse=True)[:3], start=1):
            team = home if pred == "Home" else away
            sportsbook = extra[-2]
            sims_correct = extra[-1]
            book_logo = sportsbook_logos.get(sportsbook, "")

            col1, col2, col3 = st.columns([1, 3, 2])
            with col1:
                rank_style = "gold-glow" if i == 1 else "color:#00C896;"
                st.markdown(f"<h1 style='{rank_style}margin-top:10px;'>{i}</h1>", unsafe_allow_html=True)
                safe_image(logo(team), 110, fallback_text="🏀")
                if i == 1:
                    st.markdown("<div style='color:#FFD700;font-size:1.1em;font-weight:600;'>🔥 Pick of the Day</div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                    <b style='font-size:1.3em;'>{team}</b><br>
                    <span style='color:#9DAAF2'>{metric_label}: {extra[0]}</span><br>
                    <b style='color:#00FFAE;'>Confidence: {conf}%</b><br>
                    <span style='font-size:0.9em;color:#9DAAF2;'>({sims_correct:,} out of {N_SIM:,} simulations)</span>
                """, unsafe_allow_html=True)
                st.markdown(progress_bar(conf), unsafe_allow_html=True)
            with col3:
                safe_image(book_logo, 120, fallback_text="💰", sportsbook_name=sportsbook)
            st.markdown("<hr style='border:1px solid #1C2541;'>", unsafe_allow_html=True)

    show_top("🏆 Top 3 Moneyline Predictions", top_ml, "Odds")
    show_top("📈 Top 3 Spread Predictions", top_sp, "Spread")
    show_top("🔥 Top 3 Total (O/U) Predictions", top_tot, "Total")



# ===================== TAB 2: LIVE PREDICTIONS =====================
with tab2:
    st.markdown("<div class='title'>🎯 Daily NBA Predictions</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtext'>Simulated 1,000,000x to project outcomes</div>", unsafe_allow_html=True)
    games = fetch_live_odds()

    for game in games:
        bookmaker = game["bookmakers"][0]
        home, away = game["home_team"], game["away_team"]
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
            st.markdown(f"<span class='team'><img src='{logo(away)}' width='30'> {away}</span><br>"
                        f"<span class='team'><img src='{logo(home)}' width='30'> {home}</span><br>"
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
                st.markdown(f"<div class='scoreboard'>{row['away_team']} vs {row['home_team']}<br>"
                            f"Moneyline: {row['moneyline_pred']} ({row['moneyline_conf']}%) | "
                            f"Spread: {row['spread_pred']} ({row['spread_conf']}%) | "
                            f"Total: {row['total_pred']} ({row['total_conf']}%)</div>", unsafe_allow_html=True)
        else:
            st.info("No games predicted yet.")

    with st.expander("📜 Historical Predictions"):
        if os.path.exists(DATA_FILE):
            df = pd.read_csv(DATA_FILE)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No historical data available.")

# ===================== TAB 4: RECENT WINS =====================
with tab4:
    st.markdown("<div class='title'>✅ Recent Wins & Accuracy</div>", unsafe_allow_html=True)

    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        correct_ml = np.sum(df["moneyline_result"] == "win")
        correct_sp = np.sum(df["spread_result"] == "win")
        correct_tot = np.sum(df["total_result"] == "win")
        total_ml = len(df)
        win_pct_ml = round((correct_ml / total_ml) * 100, 2) if total_ml else 0
        win_pct_sp = round((correct_sp / total_ml) * 100, 2) if total_ml else 0
        win_pct_tot = round((correct_tot / total_ml) * 100, 2) if total_ml else 0

        st.markdown(f"**Moneyline Accuracy:** 🏆 {win_pct_ml}%")
        st.markdown(f"**Spread Accuracy:** 📈 {win_pct_sp}%")
        st.markdown(f"**Total (O/U) Accuracy:** 🔥 {win_pct_tot}%")

        recent_wins = df[(df["moneyline_result"] == "win") | (df["spread_result"] == "win") | (df["total_result"] == "win")]
        st.markdown("### 🏁 Recent Winning Predictions")
        for _, row in recent_wins.tail(10).iterrows():
            st.markdown(f"<div class='scoreboard'>{row['away_team']} vs {row['home_team']}<br>"
                        f"✅ Moneyline: {row['moneyline_pred']} ({row['moneyline_conf']}%) | "
                        f"✅ Spread: {row['spread_pred']} ({row['spread_conf']}%) | "
                        f"✅ Total: {row['total_pred']} ({row['total_conf']}%)</div>", unsafe_allow_html=True)
    else:
        st.info("No historical data available yet.")
