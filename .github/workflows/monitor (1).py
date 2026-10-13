#!/usr/bin/env python3
"""
Monitor de ingressos - Luan Santana | Além do Registro (Barreiras)
Avisa por e-mail e/ou WhatsApp quando um novo lote da "Área VIP Te Vivo" abrir.

Só usa a biblioteca padrão do Python (nenhuma instalação necessária).
Configuração por variáveis de ambiente (veja README.md).
"""
import json
import os
import re
import smtplib
import ssl
import sys
import time
import urllib.parse
import urllib.request
from email.message import EmailMessage
from html.parser import HTMLParser
from pathlib import Path

URL = "https://alemdoregistro.com.br/barreiras-luan-santana-alem-do-registro__4121"
SETOR = os.getenv("SETOR", "área vip te vivo").lower()
STATE_FILE = Path(os.getenv("STATE_FILE", "state.json"))

LOTE_RE = re.compile(r"(Inteira|Meia)\s*-\s*Lote\s*(\d+)", re.IGNORECASE)
INDISPONIVEL = {"esgotado", "indisponível", "indisponivel", "encerrado",
                "em breve", "vendas encerradas"}


# ----------------------------------------------------------------- scraping
class _Texto(HTMLParser):
    def __init__(self):
        super().__init__()
        self.linhas, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if not self._skip:
            t = " ".join(data.split())
            if t:
                self.linhas.append(t)


def baixar_pagina() -> str:
    req = urllib.request.Request(URL, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def extrair_ingressos(html: str) -> list[dict]:
    p = _Texto()
    p.feed(html)
    L = p.linhas
    itens = []
    for i, linha in enumerate(L):
        m = LOTE_RE.fullmatch(linha)
        if not m or i == 0:
            continue
        setor = L[i - 1]
        preco = L[i + 1] if i + 1 < len(L) and L[i + 1].startswith("R$") else "?"
        status = L[i + 2].lower() if i + 2 < len(L) else ""
        tipo, lote = m.group(1).capitalize(), int(m.group(2))
        itens.append({
            "key": f"{setor}|{tipo}|{lote}",
            "setor": setor,
            "tipo": tipo,
            "lote": lote,
            "preco": preco,
            "disponivel": status not in INDISPONIVEL,
        })
    return itens


# ------------------------------------------------------------- notificações
def enviar_email(assunto: str, corpo: str):
    user, senha, dest = (os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"),
                         os.getenv("EMAIL_TO"))
    if not (user and senha and dest):
        return
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = assunto, user, dest
    msg.set_content(corpo)
    with smtplib.SMTP_SSL(os.getenv("SMTP_HOST", "smtp.gmail.com"),
                          int(os.getenv("SMTP_PORT", "465")),
                          context=ssl.create_default_context()) as s:
        s.login(user, senha)
        s.send_message(msg)
    print("E-mail enviado.")


def enviar_whatsapp(texto: str):
    """WhatsApp via CallMeBot (gratuito, não oficial). Veja README."""
    fone, key = os.getenv("WHATSAPP_PHONE"), os.getenv("CALLMEBOT_APIKEY")
    if not (fone and key):
        return
    qs = urllib.parse.urlencode({"phone": fone, "text": texto, "apikey": key})
    try:
        with urllib.request.urlopen(
                f"https://api.callmebot.com/whatsapp.php?{qs}", timeout=30) as r:
            corpo = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        corpo = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"CallMeBot HTTP {e.code}: {' '.join(corpo.split())[:300]}")
    limpo = re.sub(r"<[^>]+>", " ", corpo)
    limpo = " ".join(limpo.split())
    print(f"Resposta do CallMeBot: {limpo[:300]}")
    if "queued" not in limpo.lower():
        raise RuntimeError("CallMeBot não confirmou o envio (veja a resposta acima).")
    print("WhatsApp enviado (aceito pelo CallMeBot).")


def notificar(assunto: str, corpo: str):
    for fn, args in ((enviar_email, (assunto, corpo)),
                     (enviar_whatsapp, (f"{assunto}\n\n{corpo}",))):
        try:
            fn(*args)
        except Exception as e:  # um canal falhar não derruba o outro
            print(f"Falha em {fn.__name__}: {e}", file=sys.stderr)


# ------------------------------------------------------------------- lógica
def carregar_estado():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return None


def verificar():
    itens = extrair_ingressos(baixar_pagina())
    vip = [i for i in itens if SETOR in i["setor"].lower()]
    if not vip:
        raise RuntimeError("Nenhum ingresso do setor encontrado. "
                           "A página mudou ou o acesso foi bloqueado.")

    anterior = carregar_estado()
    primeira_vez = anterior is None
    anterior = anterior or {}

    novos = [i for i in vip if i["disponivel"] and not anterior.get(i["key"])]
    resumo = "\n".join(
        f"- {i['setor']} | {i['tipo']} - Lote {i['lote']} | {i['preco']} | "
        f"{'DISPONÍVEL' if i['disponivel'] else 'esgotado'}" for i in vip)

    STATE_FILE.write_text(json.dumps(
        {**anterior, **{i["key"]: i["disponivel"] for i in vip}},
        ensure_ascii=False, indent=2))

    if primeira_vez:
        notificar("✅ Monitor de ingressos ativo",
                  f"Situação atual:\n{resumo}\n\nVou avisar quando abrir um novo lote.")
    elif novos:
        lista = "\n".join(f"- {i['tipo']} - Lote {i['lote']} ({i['preco']} + taxa)"
                          for i in novos)
        notificar("🎟️ NOVO LOTE: Área VIP Te Vivo!",
                  f"Abriu:\n{lista}\n\nCorre: {URL}")
    else:
        print("Sem novidades.\n" + resumo)


if __name__ == "__main__":
    intervalo = int(os.getenv("LOOP_SECONDS", "0"))  # 0 = roda uma vez e sai
    while True:
        try:
            verificar()
        except Exception as e:
            print(f"ERRO: {e}", file=sys.stderr)
            if not intervalo:
                sys.exit(1)
        if not intervalo:
            break
        time.sleep(intervalo)
