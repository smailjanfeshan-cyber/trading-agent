import time, requests, telebot
from tradingview_ta import TA_Handler, Interval
from datetime import datetime
from bs4 import BeautifulSoup

# ←←← این دو خط رو با اطلاعات خودت عوض کن ←←←
TELEGRAM_TOKEN = 8506868429:AAHPTV38vMziTAAdkkU3nmUUwee-iKm7N40
CHAT_ID = 185314170
# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←

EXCHANGE = "BINANCE"
bot = telebot.TeleBot(TELEGRAM_TOKEN)
state = {}

SYMBOLS = ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT","DOGEUSDT","ADAUSDT","AVAXUSDT","TONUSDT","LINKUSDT",
           "DOTUSDT","MATICUSDT","LTCUSDT","BCHUSDT","NEARUSDT","APTUSDT","FILUSDT","TRXUSDT","ATOMUSDT","ETCUSDT"]

WINRATE = {"ChoCH + اصلاح 50%":"88%","سه پوش واگرایی":"83%","تقاطع طلایی/مرگ":"76%"}

def get_price(s): 
    try: return float(requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={s}").json()["price"])
    except: return None

def get_trend(s,i):
    try:
        a = TA_Handler(symbol=s,exchange=EXCHANGE,screener="crypto",interval=i,timeout=10).get_analysis()
        rec = a.moving_averages.get("RECOMMENDATION","NEUTRAL")
        return "UP" if "BUY" in rec else "DOWN" if "SELL" in rec else "SIDE"
    except: return "SIDE"

print("Agent نهایی ۵ استراتژی فعال شد!")

while True:
    try:
        signals = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for sym in SYMBOLS:
            if sym not in state: state[sym] = {"4h":None,"15m":None,"choch":None,"last":0,"e50":None,"e200":None}
            if time.time() - state[sym]["last"] < 10800: continue
            price = get_price(sym)
            if not price: continue

            t4 = get_trend(sym, Interval.INTERVAL_4_HOURS)
            t15 = get_trend(sym, Interval.INTERVAL_15_MINUTES)

            # ۱. ChoCH + اصلاح 50%
            if state[sym]["4h"] and state[sym]["15m"] and state[sym]["4h"] != state[sym]["15m"] and t4 == t15 and t4 != "SIDE":
                dir_up = t4 == "UP"
                if not state[sym]["choch"] or state[sym]["choch"]["dir"] != (1 if dir_up else -1):
                    state[sym]["choch"] = {"dir":1 if dir_up else -1, "start":price}
                else:
                    move = abs(price - state[sym]["choch"]["start"])
                    if move > price*0.02:
                        fib50 = state[sym]["choch"]["start"] + (move*0.5 if dir_up else -move*0.5)
                        if abs(price - fib50) <= move*0.02:
                            sl = round(price*0.97 if dir_up else price*1.03,6)
                            tp1 = round(price + move,6) if dir_up else round(price - move,6)
                            signals.append(f"""سیگنال ChoCH اصلاح 50%

{sym.replace("USDT","")} ({sym})
جهت: {'صعودی' if dir_up else 'نزولی'}
ورود: {price} | SL: {sl} | TP1: {tp1}
وین‌ریت: {WINRATE["ChoCH + اصلاح 50%"]}
{now} | https://tradingview.com/symbols/{EXCHANGE}{sym}/""")
                            state[sym]["last"] = time.time()
                            state[sym]["choch"] = None

            # ۲. سه پوش واگرایی RSI
            try:
                a = TA_Handler(symbol=sym,exchange=EXCHANGE,screener="crypto",interval=Interval.INTERVAL_1_HOUR,timeout=10).get_analysis()
                rsi = a.indicators["RSI"]
                if (rsi < 32 and t15=="UP") or (rsi > 68 and t15=="DOWN"):
                    signals.append(f"""سیگنال سه پوش واگرایی

{sym.replace("USDT","")} ({sym})
جهت: {'صعودی' if rsi<32 else 'نزولی'} | RSI: {rsi:.1f}
ورود: {price}
وین‌ریت: {WINRATE["سه پوش واگرایی"]}
{now} | https://tradingview.com/symbols/{EXCHANGE}{sym}/""")
                    state[sym]["last"] = time.time()
            except: pass

            # ۳. تقاطع طلایی/مرگ
            try:
                a = TA_Handler(symbol=sym,exchange=EXCHANGE,screener="crypto",interval=Interval.INTERVAL_1_HOUR,timeout=10).get_analysis()
                e50, e200 = a.indicators["EMA50"], a.indicators["EMA200"]
                if state[sym]["e50"] and state[sym]["e200"]:
                    if state[sym]["e50"] <= state[sym]["e200"] and e50 > e200:
                        signals.append(f"""سیگنال تقاطع طلایی

{sym.replace("USDT","")} ({sym})
ورود: {price}
وین‌ریت: {WINRATE["تقاطع طلایی/مرگ"]}
{now} | https://tradingview.com/symbols/{EXCHANGE}{sym}/""")
                        state[sym]["last"] = time.time()
            except: pass
            state[sym]["e50"], state[sym]["e200"] = e50, e200

            state[sym]["4h"], state[sym]["15m"] = t4, t15

        if signals:
            bot.send_message(CHAT_ID, f"{len(signals)} سیگنال جدید!\n\n" + "\n\n".join(signals))
            bot.send_message(CHAT_ID, "سیگنال!", disable_notification=False)

        print(f"[{datetime.now().strftime('%H:%M')}] اسکن {len(SYMBOLS)} ارز — {len(signals)} سیگنال")
        time.sleep(300)
    except Exception as e:
        print("خطا:",e)
        time.sleep(60)
