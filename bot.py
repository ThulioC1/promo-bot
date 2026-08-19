import os
import time
import json
import threading
import requests
from dotenv import load_dotenv
from flask import Flask

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do Telegram e do Bot
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SEARCH_TERMS = os.getenv("SEARCH_TERMS", "").strip()
MIN_DISCOUNT = float(os.getenv("MIN_DISCOUNT", "0"))
CHECK_INTERVAL = int(os.getenv("INTERVAL", "300"))
ML_AFFILIATE = os.getenv("ML_AFFILIATE", "")
FOOTER_TEXT = os.getenv("FOOTER", "🔗 Links afiliados: posso ganhar comissao sem custo extra para voce.")

BLOCK_WORDS = [word.strip().lower() for word in os.getenv("BLOCK_WORDS", "usado,recondicionado").split(",") if word.strip()]
SEEN_FILE = "seen.json"

# Inicializa o Flask para manter o app acordado no Render
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot do Mercado Livre rodando com sucesso! 🚀"

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
    terms = [t.strip() for t in SEARCH_TERMS.split(",")] if SEARCH_TERMS else ["ofertas", "promocao", "smartphone", "tecnologia"]
    
    for term in terms:
        if not term:
            continue
        url = f"https://api.mercadolibre.com/sites/MLB/search?q={term}&limit=10"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                items = data.get("results", [])
                for item in items:
                    all_products.append(item)
            else:
                print(f"Erro ao buscar termo '{term}': Status {response.status_code}")
        except Exception as e:
            print(f"Erro de conexão ao buscar '{term}': {e}")
            
    return all_products

def send_telegram_photo(photo_url, caption, reply_markup):
    """Envia foto com legenda e botão usando diretamente a API HTTP do Telegram."""
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
    seen_products = load_seen()
    
    print("Buscando novos produtos na API do Mercado Livre...")
    products = fetch_mercado_libre_products()
    print(f"Total de produtos encontrados na busca: {len(products)}")
    
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
        
        # Monta a mensagem formatada
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
        
        # Estrutura do botão inline do Telegram
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛒 VER OFERTA", "url": affiliate_link}]
            ]
        }
        
        result = send_telegram_photo(thumbnail, message, reply_markup)
        if result.get("ok"):
            print(f"Oferta enviada com sucesso: {title}")
        else:
            print(f"Falha ao enviar oferta '{title}': {result}")
            
        time.sleep(2)

def run_bot_loop():
    print("Loop do bot iniciado em background!")
    # Pequena pausa inicial para garantir que o servidor web subiu primeiro
    time.sleep(5)
    while True:
        try:
            process_and_send_offers()
        except Exception as e:
            print(f"Erro no ciclo principal do bot: {e}")
        
        print(f"Aguardando {CHECK_INTERVAL} segundos para a próxima varredura...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # Inicia o loop do bot em uma thread separada
    bot_thread = threading.Thread(target=run_bot_loop, daemon=True)
    bot_thread.start()
    
    # Roda o Flask na porta exigida pelo Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)