import os
import time
import json
import threading
import requests
from curl_cffi import requests as curl_requests
from dotenv import load_dotenv
from flask import Flask

# Carrega variáveis de ambiente
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

# Controle de thread
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

def fetch_mercado_libre_products():
    all_products = []
    terms = [t.strip() for t in SEARCH_TERMS.split(",")] if SEARCH_TERMS else ["smartphone", "notebook"]
    
    print(f"[{time.strftime('%X')}] Buscando na API do ML para: {terms}")
    for term in terms:
        if not term: continue
        url = f"https://api.mercadolibre.com/sites/MLB/search?q={term}&limit=5"
        try:
            # impersonate="chrome" burla o bloqueio de bot da API
            response = curl_requests.get(url, impersonate="chrome", timeout=15)
            if response.status_code == 200:
                data = response.json()
                items = data.get("results", [])
                print(f"[{time.strftime('%X')}] Termo '{term}': {len(items)} produtos encontrados.")
                for item in items:
                    all_products.append(item)
            else:
                print(f"Erro ao buscar termo '{term}': Status {response.status_code}")
        except Exception as e:
            print(f"Erro de conexão: {e}")
    return all_products

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
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erro Telegram: {e}")

def process_and_send_offers():
    print("--- INICIANDO CICLO ---")
    seen_products = load_seen()
    products = fetch_mercado_libre_products()
    
    for item in products:
        item_id = item.get("id")
        if item_id in seen_products: continue
            
        title = item.get("title", "")
        price = item.get("price", 0)
        # API do ML retorna o preço original no campo 'original_price'
        original_price = item.get("original_price")
        permalink = item.get("permalink", "")
        thumbnail = item.get("thumbnail", "").replace("http://", "https://")
        
        if any(block in title.lower() for block in BLOCK_WORDS): continue
            
        discount = 0
        if original_price and original_price > price:
            discount = int(((original_price - price) / original_price) * 100)
            
        if MIN_DISCOUNT > 0 and discount < MIN_DISCOUNT: continue
            
        seen_products.append(item_id)
        save_seen(seen_products)
        
        message = f"🔥 *OFERTA*\n\n📦 *{title}*\n\n💰 R$ {price:.2f}"
        if discount > 0: message += f"\n🏷️ *{discount}% OFF*"
        message += f"\n\n_{FOOTER_TEXT}_"
        
        reply_markup = {"inline_keyboard": [[{"text": "🛒 VER OFERTA", "url": generate_affiliate_link(permalink)}]]}
        send_telegram_photo(thumbnail, message, reply_markup)
        time.sleep(2)

def run_bot_loop():
    while True:
        try:
            process_and_send_offers()
        except Exception as e:
            print(f"Erro ciclo: {e}")
        time.sleep(CHECK_INTERVAL)

@app.route("/")
def home():
    global _bot_thread_started
    with _lock:
        if not _bot_thread_started:
            _bot_thread_started = True
            threading.Thread(target=run_bot_loop, daemon=True).start()
    return "Bot rodando! 🚀"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))