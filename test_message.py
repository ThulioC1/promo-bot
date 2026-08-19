import bot

# promos de exemplo para validar formatacao + afiliado + rodape
amazon = {
    "id": "test-amazon",
    "title": "TESTE - Notebook Dell Inspiron 50% OFF",
    "price": 2499.90,
    "old_price": 4999.90,
    "discount": 50,
    "store": "Amazon",
    "url": "https://www.amazon.com.br/notebook-dell/dp/B09TESTE",
    "coupon": None,
}
ml = {
    "id": "test-ml",
    "title": "TESTE - Fone Bluetooth Redmi Buds",
    "price": 99.90,
    "old_price": 199.90,
    "discount": 50,
    "store": "Mercado Livre",
    "url": "https://produto.mercadolivre.com.br/MLB-123456",
    "coupon": None,
    "image": "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_92x30dp.png",
}

for label, d in [("AMAZON", amazon), ("ML", ml)]:
    msg = bot.fmt(d)
    with open(f"test_msg_{label}.txt", "w", encoding="utf-8") as f:
        f.write(msg)
    try:
        bot.send_deal(d)
        print(f"[{label}] enviada ao Telegram! (mensagem salva em test_msg_{label}.txt)")
    except Exception as e:
        print(f"[{label}] ERRO ao enviar:", e)
