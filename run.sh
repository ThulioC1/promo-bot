#!/bin/bash
# Mantem o bot rodando: reinicia automaticamente se cair.
# Ativa o venv se existir, para encontrar as libs instaladas.
# Uso: nohup bash run.sh > bot.log 2>&1 &
VENV=venv
[ -d "$VENV" ] && source "$VENV/bin/activate"
while true; do
  echo "[$(date)] Iniciando bot..."
  python bot.py
  echo "[$(date)] Bot parou. Reiniciando em 5s..."
  sleep 5
done
