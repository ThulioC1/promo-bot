import os
import time
import json
import threading
import requests
from curl_cffi import requests as curl_requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SEARCH_TERMS = os.getenv("SEARCH_TERMS", "").strip()
MIN_DISCOUNT = float(os.getenv("MIN_DISCOUNT", "0"))
CHECK_INTERVAL = int(os.getenv("INTERVAL", "300"))
ML_AFFILIATE = os.getenv("ML_AFFILIATE", "")
FOOTER_TEXT = os.getenv("FOOTER", "🔗 Links afiliados: posso ganhar comissao sem custo extra para voce.")

BLOCK_WORDS = [word.strip().lower() for word in os.getenv("BLOCK_WORDS", "usado,recondicionado").split(",") if word.strip()]
SEEN_FILE = "seen.json"

app = Flask(__name__)

# Controle de concorrência para iniciar a thread apenas uma vez
_bot_thread_started = False
_lock = threading.Lock()

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_seen(seen_list):
    if len(seen_list) > 500:
        seen_list = seen_list[-500:]
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen_list, f, ensure_ascii=False, indent=4)

def generate_affiliate_link(original_url):
    if not ML_AFFILIATE:
        return original_url
    clean_url = original_url.split("?")[0]
    affiliate_suffix = f"/{ML_AFFILIATE}" if not ML_AFFILIATE.startswith("/") else ML_AFFILIATE
    return f"{clean_url}?matt_tool={affiliate_suffix.replace('social/', '')}"



def send_telegram_photo(photo_url, caption, reply_markup):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(reply_markup)
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Erro ao enviar requisição para o Telegram: {e}")
        return {"ok": False}

def process_and_send_offers():
    print("--- INICIANDO NOVO CICLO DE VARREDURA (WEB SCRAPING) ---")
    seen_products = load_seen()
    products = fetch_mercado_libre_products()
    print(f"Total acumulado de produtos válidos: {len(products)}")
    
    for item in products:
        item_id = item.get("id")
        if item_id in seen_products:
            continue
            
        title = item.get("title", "")
        price = item.get("price", 0)
        original_price = item.get("original_price")
        permalink = item.get("permalink", "")
        thumbnail = item.get("thumbnail", "").replace("http://", "https://")
        
        title_lower = title.lower()
        if any(block_word in title_lower for block_word in BLOCK_WORDS):
            continue
            
        discount = 0
        if original_price and original_price > price:
            discount = int(((original_price - price) / original_price) * 100)
            
        if MIN_DISCOUNT > 0 and discount < MIN_DISCOUNT:
            continue
            
        seen_products.append(item_id)
        save_seen(seen_products)
        
        message = (
            f"🔥 *OFERTA DO MERCADO LIVRE*\n\n"
            f"📦 *{title}*\n\n"
            f"💰 Por apenas *R$ {price:.2f}*\n"
        )
        
        if original_price and original_price > price:
            message += f"📉 De R$ {original_price:.2f}\n"
            message += f"🏷️ *{discount}% OFF*\n\n"
        else:
            message += "\n"
            
        message += f"🏪 Mercado Livre\n\n_{FOOTER_TEXT}_"
        
        affiliate_link = generate_affiliate_link(permalink)
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛒 VER OFERTA", "url": affiliate_link}]
            ]
        }
        
        if thumbnail:
            result = send_telegram_photo(thumbnail, message, reply_markup)
        else:
            result = {"ok": True}
            
        if result.get("ok"):
            print(f"SUCESSO: Oferta enviada -> {title}")
        else:
            print(f"FALHA NO TELEGRAM para '{title}': {result}")
            
        time.sleep(2)

def run_bot_loop():
    print(">>> THREAD DO BOT DE SCRAPING INICIADA COM SUCESSO! <<<")
    while True:
        try:
            process_and_send_offers()
        except Exception as e:
            print(f"Erro crítico no ciclo do bot: {e}")
        
        print(f"Ciclo finalizado. Dormindo por {CHECK_INTERVAL} segundos...")
        time.sleep(CHECK_INTERVAL)

def start_bot_background():
    global _bot_thread_started
    with _lock:
        if not _bot_thread_started:
            _bot_thread_started = True
            bot_thread = threading.Thread(target=run_bot_loop, daemon=True)
            bot_thread.start()

@app.route("/")
def home():
    start_bot_background()
    return "Bot de Scraping do Mercado Livre rodando com sucesso! 🚀"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)