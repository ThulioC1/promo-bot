import os
import time
import json
import requests
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações do Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Configurações do seu .env atual
SEARCH_TERMS = os.getenv("SEARCH_TERMS", "").strip()
MIN_DISCOUNT = float(os.getenv("MIN_DISCOUNT", "0"))
CHECK_INTERVAL = int(os.getenv("INTERVAL", "300"))
ML_AFFILIATE = os.getenv("ML_AFFILIATE", "")
FOOTER_TEXT = os.getenv("FOOTER", "🔗 Links afiliados: posso ganhar comissao sem custo extra para voce.")

# Palavras bloqueadas (caso queira adicionar no futuro)
BLOCK_WORDS = [word.strip().lower() for word in os.getenv("BLOCK_WORDS", "usado,recondicionado").split(",") if word.strip()]

SEEN_FILE = "seen.json"

def load_seen():
    """Carrega a lista de produtos já enviados para evitar repetição."""
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_seen(seen_list):
    """Salva a lista atualizada de produtos vistos."""
    if len(seen_list) > 500:
        seen_list = seen_list[-500:]
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen_list, f, ensure_ascii=False, indent=4)

def generate_affiliate_link(original_url):
    """
    Transforma o link original do Mercado Livre usando o seu sufixo de afiliado.
    Exemplo: insere o sufixo de rastreio no link do produto.
    """
    if not ML_AFFILIATE:
        return original_url
    
    # Remove qualquer barra dupla e anexa o sufixo de afiliado de forma segura
    clean_url = original_url.split("?")[0] # Remove parâmetros antigos de tracking se houver
    if not ML_AFFILIATE.startswith("/"):
        affiliate_suffix = f"/{ML_AFFILIATE}"
    else:
        affiliate_suffix = ML_AFFILIATE
        
    return f"{clean_url}?matt_tool={affiliate_suffix.replace('social/', '')}" # Ajuste conforme o padrão do seu link de afiliado do ML

def fetch_mercado_libre_products():
    """Busca produtos na API oficial do Mercado Livre."""
    all_products = []
    
    # Se SEARCH_TERMS estiver vazio, define um termo genérico de ofertas para não falhar
    terms = [t.strip() for t in SEARCH_TERMS.split(",")] if SEARCH_TERMS else ["ofertas", "promocao", "smartphone"]
    
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

def process_and_send_offers():
    bot = Bot(token=TELEGRAM_TOKEN)
    seen_products = load_seen()
    
    print("Buscando novos produtos na API do Mercado Livre...")
    products = fetch_mercado_libre_products()
    
    for item in products:
        item_id = item.get("id")
        
        if item_id in seen_products:
            continue
            
        title = item.get("title", "")
        price = item.get("price", 0)
        original_price = item.get("original_price")
        permalink = item.get("permalink", "")
        thumbnail = item.get("thumbnail", "").replace("http://", "https://")
        
        # Filtro de palavras bloqueadas
        title_lower = title.lower()
        if any(block_word in title_lower for block_word in BLOCK_WORDS):
            continue
            
        # Cálculo de desconto
        discount = 0
        if original_price and original_price > price:
            discount = int(((original_price - price) / original_price) * 100)
            
        # Filtro de desconto mínimo (se MIN_DISCOUNT for maior que 0)
        if MIN_DISCOUNT > 0 and discount < MIN_DISCOUNT:
            continue
            
        # Marca como visto
        seen_products.append(item_id)
        save_seen(seen_products)
        
        # Monta a mensagem estruturada
        message = (
            f"🔥 **OFERTA DO MERCADO LIVRE**\n\n"
            f"📦 **{title}**\n\n"
            f"💰 Por apenas **R$ {price:.2f}**\n"
        )
        
        if original_price and original_price > price:
            message += f"📉 De R$ {original_price:.2f}\n"
            message += f"🏷️ **{discount}% OFF**\n\n"
        else:
            message += "\n"
            
        message += (
            f"🏪 Mercado Livre\n\n"
            f"_{FOOTER_TEXT}_"
        )
        
        affiliate_link = generate_affiliate_link(permalink)
        keyboard = [[InlineKeyboardButton("🛒 VER OFERTA", url=affiliate_link)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            if thumbnail:
                bot.send_photo(
                    chat_id=TELEGRAM_CHAT_ID,
                    photo=thumbnail,
                    caption=message,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
            else:
                bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=message,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
            print(f"Oferta enviada: {title}")
            time.sleep(2)
        except Exception as e:
            print(f"Erro ao enviar para o Telegram: {e}")

if __name__ == "__main__":
    print("Bot do Mercado Livre iniciado!")
    while True:
        try:
            process_and_send_offers()
        except Exception as e:
            print(f"Erro no ciclo principal: {e}")
        
        print(f"Aguardando {CHECK_INTERVAL} segundos...")
        time.sleep(CHECK_INTERVAL)