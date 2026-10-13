# Monitor de ingressos – Área VIP Te Vivo (Luan Santana, Barreiras)

Avisa por e-mail e/ou WhatsApp quando abrir um **novo lote** (ou um lote
esgotado voltar) da Área VIP Te Vivo.

## Opção A – Grátis na nuvem (GitHub Actions) – recomendado
1. Crie um repositório **público** no GitHub (público = minutos ilimitados;
   seus dados ficam em *Secrets*, não aparecem).
2. Suba estes arquivos (`monitor.py` e `.github/workflows/monitor.yml`).
3. Em *Settings → Secrets and variables → Actions*, crie os secrets abaixo.
4. Aba *Actions* → "Monitor de ingressos" → *Run workflow*. Você receberá
   uma mensagem "Monitor ativo" confirmando que funciona.

## Opção B – No seu PC/servidor
```
export EMAIL_USER=... EMAIL_PASS=... EMAIL_TO=...
export LOOP_SECONDS=300
python3 monitor.py
```

## Secrets / variáveis
**E-mail (Gmail):** `EMAIL_USER` (seu gmail), `EMAIL_PASS` (senha de app),
`EMAIL_TO` (destino). Senha de app: myaccount.google.com → Segurança →
Verificação em duas etapas → Senhas de app.

**WhatsApp (CallMeBot, gratuito):** envie "I allow callmebot to send me messages"
para +34 644 51 95 23 no WhatsApp; ele responde com sua `apikey`.
Secrets: `WHATSAPP_PHONE` (ex.: `5577999999999`) e `CALLMEBOT_APIKEY`.

Configure um dos canais ou os dois.
