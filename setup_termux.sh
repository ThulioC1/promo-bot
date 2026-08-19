#!/bin/bash
# Setup para Termux (Redmi Note 10). Rode: bash setup_termux.sh
set -e

pkg update -y && pkg upgrade -y
pkg install -y python git
# cria ambiente virtual (contorna a restricao de pip do Termux)
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# mantem o processador/acordo ativo com a tela fechada
termux-wake-lock

echo ""
echo "==========================================="
echo "1) Confira o .env (TOKEN e CHAT_ID)"
echo "2) Rode o bot com reinicio automatico:"
echo "   nohup bash run.sh > bot.log 2>&1 &"
echo "3) Veja os logs:  tail -f bot.log"
echo "==========================================="
