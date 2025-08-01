import requests
from bs4 import BeautifulSoup
import telebot
import time
from datetime import datetime, timedelta

# === CONFIG ===
TOKEN = "8426877567:AAG32OkXiBBtZdI3w1032_uYHyHxKU9WV3w"
CHAT_ID = "6567090796"
BANKROLL = 1_000_000
bot = telebot.TeleBot(TOKEN)
HEADERS = {"User-Agent": "Mozilla/5.0"}

# === FETCH MELBET UPCOMING ODDS ===
def get_melbet_odds():
    odds = {}
    try:
        now_ts = int(datetime.now().timestamp())
        future_ts = int((datetime.now() + timedelta(days=3)).timestamp())
        sports = {1: "Football", 4: "Tennis"}  # Melbet sport IDs
        for sport_id in sports:
            url = f"https://melbet.ru/LineFeed/Get1x2_VZip?sport={sport_id}&count=1000&mode=4"
            r = requests.get(url, headers=HEADERS, timeout=10)
            data = r.json()
            for event in data.get("Value", []):
                start_ts = int(event.get("StartTime", 0))
                if now_ts <= start_ts <= future_ts:
                    team1 = event.get("O1")
                    team2 = event.get("O2")
                    match = f"{team1} vs {team2}"
                    outcome1 = event.get("E1")
                    outcome2 = event.get("E2")
                    draw = event.get("E0")
                    if all([outcome1, draw, outcome2]):
                        odds[match] = [float(outcome1), float(draw), float(outcome2)]
    except Exception as e:
        print("Melbet error:", e)
    return odds

# === FETCH BETPAWA UPCOMING ODDS ===
def get_betpawa_odds():
    odds = {}
    try:
        urls = [
            "https://www.betpawa.cm/api/markets/football",
            "https://www.betpawa.cm/api/markets/tennis"
        ]
        for url in urls:
            r = requests.get(url, headers=HEADERS, timeout=10)
            data = r.json()
            for event in data.get("events", []):
                team1 = event.get("home_team")
                team2 = event.get("away_team")
                match = f"{team1} vs {team2}"
                outcomes = event.get("odds", [])
                if len(outcomes) >= 3:
                    try:
                        o1 = float(outcomes[0]["value"])
                        draw = float(outcomes[1]["value"])
                        o2 = float(outcomes[2]["value"])
                        odds[match] = [o1, draw, o2]
                    except:
                        continue
    except Exception as e:
        print("Betpawa error:", e)
    return odds

# === ARBITRAGE CALCULATION ===
def calc_arbitrage(odds1, odds2):
    best_odds = [max(o1, o2) for o1, o2 in zip(odds1, odds2)]
    inv_sum = sum(1 / o for o in best_odds)
    margin = inv_sum * 100
    if margin < 100:
        stake1 = BANKROLL * (1 / best_odds[0]) / inv_sum
        stake2 = BANKROLL * (1 / best_odds[1]) / inv_sum
        stake3 = BANKROLL * (1 / best_odds[2]) / inv_sum
        profit = min(stake1 * best_odds[0], stake2 * best_odds[1], stake3 * best_odds[2]) - BANKROLL
        return margin, round(profit)
    return margin, 0

# === BOT LOGIC ===
def check_arb():
    melbet = get_melbet_odds()
    betpawa = get_betpawa_odds()
    message = ""
    for match in melbet:
        if match in betpawa:
            mb_odds = melbet[match]
            bp_odds = betpawa[match]
            margin, profit = calc_arbitrage(mb_odds, bp_odds)
            if profit > 0:
                message += f"\ud83c\udfaf *{match}*\nMelbet: {mb_odds}\nBetpawa: {bp_odds}\nMargin: {margin:.2f}%\nProfit: {profit:,} XAF\n\n"
    return message or "\u274c No arbitrage found."

@bot.message_handler(commands=['start', 'check'])
def send_arbs(message):
    result = check_arb()
    bot.send_message(message.chat.id, result, parse_mode="Markdown")

while True:
    try:
        bot.polling()
    except Exception as e:
        print("Bot crashed, restarting...", e)
        time.sleep(5)
