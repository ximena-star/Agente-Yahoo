# -*- coding: utf-8 -*-
"""
Stock Agent — Yahoo Finance + Noticias RSS
DOW · S&P500 · Top AI Stocks  |  20x al dia
Noticias: Yahoo Finance News + Reuters RSS + MarketWatch RSS (sin API key)
"""

import yfinance as yf
import schedule
import time
import smtplib
import logging
import sys
import feedparser
import urllib.request
from groq import Groq
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import CONFIG

# ─── Logging (fix Unicode Windows) ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("stock_agent.log", encoding="utf-8"),
        logging.StreamHandler(stream=open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1, closefd=False))
    ]
)
log = logging.getLogger("StockAgent")

# ─── Simbolos a monitorear ───────────────────────────────────────────────────
SYMBOLS = {
    "^DJI":  {"name": "Dow Jones",  "category": "index", "emoji": "[DOW]"},
    "^GSPC": {"name": "S&P 500",    "category": "index", "emoji": "[S&P]"},
    "NVDA":  {"name": "NVIDIA",     "category": "ai",    "emoji": "[NVDA]"},
    "MSFT":  {"name": "Microsoft",  "category": "ai",    "emoji": "[MSFT]"},
    "GOOGL": {"name": "Alphabet",   "category": "ai",    "emoji": "[GOOGL]"},
    "META":  {"name": "Meta",       "category": "ai",    "emoji": "[META]"},
    "AMZN":  {"name": "Amazon",     "category": "ai",    "emoji": "[AMZN]"},
    "TSLA":  {"name": "Tesla",      "category": "ai",    "emoji": "[TSLA]"},
    "AAPL":  {"name": "Apple",      "category": "ai",    "emoji": "[AAPL]"},
    "AMD":   {"name": "AMD",        "category": "ai",    "emoji": "[AMD]"},
}

# ─── Fuentes RSS de noticias (sin API key) ───────────────────────────────────
RSS_MARKET_GENERAL = [
    ("Reuters Business",    "https://feeds.reuters.com/reuters/businessNews"),
    ("MarketWatch Markets", "https://feeds.content.dowjones.io/public/rss/mw_marketpulse"),
    ("Yahoo Finance",       "https://finance.yahoo.com/news/rssindex"),
]

RSS_POR_SIMBOLO = {
    "NVDA":  "https://finance.yahoo.com/rss/headline?s=NVDA",
    "MSFT":  "https://finance.yahoo.com/rss/headline?s=MSFT",
    "GOOGL": "https://finance.yahoo.com/rss/headline?s=GOOGL",
    "META":  "https://finance.yahoo.com/rss/headline?s=META",
    "AMZN":  "https://finance.yahoo.com/rss/headline?s=AMZN",
    "TSLA":  "https://finance.yahoo.com/rss/headline?s=TSLA",
    "AAPL":  "https://finance.yahoo.com/rss/headline?s=AAPL",
    "AMD":   "https://finance.yahoo.com/rss/headline?s=AMD",
    "^DJI":  "https://finance.yahoo.com/rss/headline?s=%5EDJI",
    "^GSPC": "https://finance.yahoo.com/rss/headline?s=%5EGSPC",
}

update_count = 0

# ─── 1. FETCH DE DATOS DE MERCADO ────────────────────────────────────────────
def fetch_market_data() -> dict:
    log.info("[FETCH] Consultando Yahoo Finance...")
    results = {}
    tickers = yf.Tickers(" ".join(SYMBOLS.keys()))

    for symbol, meta in SYMBOLS.items():
        try:
            ticker = tickers.tickers[symbol]
            info = ticker.fast_info
            price      = round(info.last_price, 2)
            prev_close = round(info.previous_close, 2)
            change     = round(price - prev_close, 2)
            change_pct = round((change / prev_close) * 100, 2) if prev_close else 0.0
            results[symbol] = {
                "name":       meta["name"],
                "category":   meta["category"],
                "emoji":      meta["emoji"],
                "price":      price,
                "prev_close": prev_close,
                "change":     change,
                "change_pct": change_pct,
                "direction":  "+" if change >= 0 else "-",
                "color_flag": "positive" if change >= 0 else "negative",
            }
            signo = "+" if change >= 0 else ""
            log.info(f"  {meta['emoji']} {symbol:<6} ${price:>12,.2f}  {signo}{change_pct}%")
        except Exception as e:
            log.warning(f"  [WARN] Error fetching {symbol}: {e}")

    return results

# ─── 2. FETCH DE NOTICIAS RSS ────────────────────────────────────────────────
def fetch_rss(url: str, max_items: int = 3) -> list:
    """Obtiene titulares de un feed RSS sin API key."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            content = resp.read()
        feed = feedparser.parse(content)
        items = []
        for entry in feed.entries[:max_items]:
            title = entry.get("title", "Sin titulo")
            link  = entry.get("link", "#")
            pub   = entry.get("published", "")[:16] if entry.get("published") else ""
            items.append({"title": title, "link": link, "date": pub})
        return items
    except Exception as e:
        log.warning(f"  [NEWS] Error RSS {url[:50]}: {e}")
        return []

def fetch_all_news() -> dict:
    """Obtiene noticias generales + por simbolo."""
    log.info("[NEWS] Obteniendo noticias de mercado...")
    news = {"general": [], "por_simbolo": {}}

    # Noticias generales (Reuters + MarketWatch + Yahoo)
    for source_name, url in RSS_MARKET_GENERAL:
        items = fetch_rss(url, max_items=2)
        for item in items:
            item["source"] = source_name
            news["general"].append(item)
        if items:
            log.info(f"  [NEWS] {source_name}: {len(items)} noticias")

    # Noticias por simbolo (Yahoo Finance RSS)
    ai_symbols = [s for s in SYMBOLS if SYMBOLS[s]["category"] == "ai"]
    for symbol in ai_symbols:
        url = RSS_POR_SIMBOLO.get(symbol)
        if url:
            items = fetch_rss(url, max_items=2)
            if items:
                news["por_simbolo"][symbol] = items
                log.info(f"  [NEWS] {symbol}: {len(items)} noticias")

    return news

# ─── 3. ANALISIS IA con Groq (GRATIS) ───────────────────────────────────────
def generate_ai_analysis(data: dict, news: dict) -> str:
    if not CONFIG.get("GROQ_API_KEY"):
        return "Analisis IA no configurado. Agrega GROQ_API_KEY en config.py"

    # Resumen de precios
    price_summary = [
        f"{v['name']}: ${v['price']:,.2f} ({'+' if v['change_pct']>=0 else ''}{v['change_pct']}%)"
        for v in data.values()
    ]

    # Resumen de noticias para el prompt
    news_lines = []
    for item in news["general"][:4]:
        news_lines.append(f"- [{item['source']}] {item['title']}")
    for symbol, items in list(news["por_simbolo"].items())[:4]:
        for item in items[:1]:
            news_lines.append(f"- [{symbol}] {item['title']}")

    prompt = f"""Eres un analista financiero senior. Analiza estos datos bursatiles:

PRECIOS:
{chr(10).join(price_summary)}

NOTICIAS RECIENTES:
{chr(10).join(news_lines) if news_lines else "Sin noticias disponibles"}

Redacta un analisis ejecutivo conciso en espanol (max. 4 parrafos) para un inversor en Lima, Peru.
Incluye:
1. Tendencia general del mercado considerando las noticias
2. El activo con mejor y peor desempeno y por que (basate en noticias si las hay)
3. Sector IA: estado general
4. Una micro-recomendacion de vigilancia para las proximas horas

Se directo, profesional y sin tecnicismos innecesarios."""

    try:
        client = Groq(api_key=CONFIG["GROQ_API_KEY"])
        msg = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.choices[0].message.content
    except Exception as e:
        log.error(f"Error en analisis IA: {e}")
        return f"Error al generar analisis: {e}"

# ─── 4. CONSTRUIR EMAIL HTML ─────────────────────────────────────────────────
def build_email_html(data: dict, analysis: str, news: dict, update_num: int) -> tuple:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    indices   = {k: v for k, v in data.items() if v["category"] == "index"}
    ai_stocks = {k: v for k, v in data.items() if v["category"] == "ai"}

    def row_color(flag):
        return "#1a3a1a" if flag == "positive" else "#3a1a1a"

    def text_color(flag):
        return "#7fff6e" if flag == "positive" else "#ff6b6b"

    # Tabla indices
    index_rows = ""
    for sym, v in indices.items():
        c = text_color(v["color_flag"])
        signo = "+" if v["change_pct"] >= 0 else ""
        index_rows += f"""
        <tr style="background:{row_color(v['color_flag'])};border-bottom:1px solid #2a2a2a">
          <td style="padding:12px 16px;font-size:14px;font-weight:bold;color:#aaa">{sym}</td>
          <td style="padding:12px 8px"><b style="color:#e0e0e0">{v['name']}</b></td>
          <td style="padding:12px;text-align:right;font-size:20px;font-weight:bold;color:#fff;font-family:monospace">
              ${v['price']:>12,.2f}</td>
          <td style="padding:12px 16px;text-align:right;color:{c};font-size:14px;font-weight:bold">
              {v['direction']} ${abs(v['change']):,.2f}<br>
              <span style="font-size:12px">{signo}{v['change_pct']}%</span></td>
        </tr>"""

    # Tabla AI stocks
    ai_rows = ""
    for sym, v in ai_stocks.items():
        c = text_color(v["color_flag"])
        signo = "+" if v["change_pct"] >= 0 else ""
        # Noticias del simbolo (1 titular)
        noticia_sym = ""
        if sym in news["por_simbolo"] and news["por_simbolo"][sym]:
            n = news["por_simbolo"][sym][0]
            noticia_sym = f'<br><a href="{n["link"]}" style="font-size:10px;color:#555;text-decoration:none">&#128240; {n["title"][:70]}...</a>'
        ai_rows += f"""
        <tr style="border-bottom:1px solid #1a1a1a">
          <td style="padding:10px 16px;font-weight:bold;color:#aaa">{sym}</td>
          <td style="padding:10px;color:#aaa;font-size:12px">{v['name']}{noticia_sym}</td>
          <td style="padding:10px;text-align:right;font-family:monospace;color:#fff">${v['price']:,.2f}</td>
          <td style="padding:10px 16px;text-align:right;color:{c};font-size:13px">
              {v['direction']} {signo}{v['change_pct']}%</td>
        </tr>"""

    # Seccion noticias generales
    noticias_html = ""
    if news["general"]:
        for item in news["general"][:5]:
            noticias_html += f"""
            <tr style="border-bottom:1px solid #1a1a1a">
              <td style="padding:8px 16px">
                <span style="font-size:10px;color:#00d4ff;font-weight:bold">{item.get('source','')}</span>
                <a href="{item['link']}" style="display:block;font-size:12px;color:#c0c0c0;text-decoration:none;margin-top:2px">
                  {item['title'][:100]}
                </a>
                <span style="font-size:10px;color:#444">{item.get('date','')}</span>
              </td>
            </tr>"""

    analysis_html = analysis.replace("\n", "<br>")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:20px;background:#080808;font-family:'Courier New',monospace;color:#c0c0c0">
<div style="max-width:660px;margin:0 auto">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#0d1117,#161b22);border:1px solid #30363d;border-radius:10px 10px 0 0;padding:24px">
    <table width="100%"><tr>
      <td><h1 style="margin:0;color:#00d4ff;font-size:22px;letter-spacing:2px">STOCK AGENT</h1>
          <p style="margin:6px 0 0;color:#555;font-size:12px">Actualizacion #{update_num} de 20 &middot; {now} (Lima, PE)</p></td>
      <td style="text-align:right"><span style="background:#0d2a0d;border:1px solid #3a7a3a;color:#7fff6e;
          padding:6px 14px;border-radius:20px;font-size:11px;font-weight:bold">LIVE</span></td>
    </tr></table>
  </div>

  <!-- Indices -->
  <div style="border:1px solid #30363d;border-top:none">
    <div style="background:#0d1117;padding:10px 16px;border-bottom:1px solid #30363d">
      <span style="font-size:10px;color:#555;letter-spacing:3px">INDICES PRINCIPALES</span>
    </div>
    <table width="100%" style="border-collapse:collapse;background:#0a0a0a">{index_rows}</table>
  </div>

  <!-- AI Stocks -->
  <div style="border:1px solid #30363d;border-top:none">
    <div style="background:#0d1117;padding:10px 16px;border-bottom:1px solid #30363d">
      <span style="font-size:10px;color:#555;letter-spacing:3px">TOP AI STOCKS</span>
    </div>
    <table width="100%" style="border-collapse:collapse;background:#090909">{ai_rows}</table>
  </div>

  <!-- Analisis IA -->
  <div style="border:1px solid #30363d;border-top:none;background:#0a0d0a;padding:20px">
    <div style="font-size:10px;color:#00d4ff;letter-spacing:3px;margin-bottom:12px">ANALISIS IA (Groq + LLaMA)</div>
    <div style="font-size:13px;color:#9a9a9a;line-height:1.8">{analysis_html}</div>
  </div>

  <!-- Noticias Generales -->
  <div style="border:1px solid #30363d;border-top:none;background:#080a08">
    <div style="background:#0d1117;padding:10px 16px;border-bottom:1px solid #30363d">
      <span style="font-size:10px;color:#555;letter-spacing:3px">NOTICIAS DE MERCADO</span>
      <span style="font-size:9px;color:#333;margin-left:8px">Reuters &middot; MarketWatch &middot; Yahoo Finance</span>
    </div>
    <table width="100%" style="border-collapse:collapse">{noticias_html if noticias_html else '<tr><td style="padding:12px 16px;color:#444;font-size:12px">Sin noticias disponibles en este momento.</td></tr>'}</table>
  </div>

  <!-- Footer -->
  <div style="background:#050505;border:1px solid #1a1a1a;border-top:none;border-radius:0 0 10px 10px;
       padding:14px 16px;text-align:center;font-size:10px;color:#333">
    Stock Agent &middot; Lima, Peru &middot; {now} &middot; Proxima actualizacion en ~72 min<br>
    Fuentes: Yahoo Finance &middot; Reuters RSS &middot; MarketWatch RSS
  </div>

</div></body></html>"""

    # Texto plano
    plain = f"STOCK AGENT — Update #{update_num} — {now}\n{'='*50}\n"
    for sym, v in data.items():
        signo = "+" if v["change_pct"] >= 0 else ""
        plain += f"{sym:<6} {v['name']:<12} ${v['price']:>12,.2f}  {signo}{v['change_pct']}%\n"
    plain += f"\n{'='*50}\nANALISIS IA:\n{analysis}\n"
    plain += f"\n{'='*50}\nNOTICIAS:\n"
    for item in news["general"][:5]:
        plain += f"- [{item.get('source','')}] {item['title']}\n"

    return html, plain

# ─── 5. ENVIAR EMAIL ─────────────────────────────────────────────────────────
def send_email(html: str, plain: str, update_num: int):
    cfg = CONFIG
    if not all([cfg.get("EMAIL_FROM"), cfg.get("EMAIL_TO"), cfg.get("SMTP_PASSWORD")]):
        log.warning("[WARN] Email no configurado. Revisa config.py")
        return

    subject = f"Stock Agent #{update_num}/20 — {datetime.now().strftime('%H:%M')} | DOW & S&P500 + Noticias"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = cfg["EMAIL_FROM"]
    msg["To"]      = cfg["EMAIL_TO"]
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html,  "html",  "utf-8"))

    try:
        with smtplib.SMTP_SSL(cfg["SMTP_HOST"], cfg["SMTP_PORT"]) as server:
            server.login(cfg["EMAIL_FROM"], cfg["SMTP_PASSWORD"])
            server.sendmail(cfg["EMAIL_FROM"], cfg["EMAIL_TO"], msg.as_string())
        log.info(f"[OK] Email #{update_num} enviado a {cfg['EMAIL_TO']}")
    except Exception as e:
        log.error(f"[ERROR] Error enviando email: {e}")

# ─── 6. TAREA PRINCIPAL ──────────────────────────────────────────────────────
def run_update():
    global update_count
    update_count += 1
    log.info(f"\n{'='*55}")
    log.info(f"  UPDATE #{update_count}/20  |  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    log.info(f"{'='*55}")

    data        = fetch_market_data()
    news        = fetch_all_news()
    analysis    = generate_ai_analysis(data, news)
    html, plain = build_email_html(data, analysis, news, update_count)
    send_email(html, plain, update_count)

    if update_count >= 20:
        log.info("[OK] 20 actualizaciones completadas. Reiniciando contador.")
        update_count = 0

# ─── 7. SCHEDULER ────────────────────────────────────────────────────────────
def start_scheduler():
    log.info("[START] Stock Agent iniciado. Programando 20 actualizaciones diarias...")

    horarios = [
        "06:00", "07:12", "08:24", "09:36", "10:48",
        "12:00", "13:12", "14:24", "15:36", "16:48",
        "18:00", "19:12", "20:24", "21:36", "22:48",
        "09:30", "11:00", "14:00", "16:00", "21:00",
    ]
    horarios_unicos = sorted(set(horarios))

    for hora in horarios_unicos:
        schedule.every().day.at(hora).do(run_update)
        log.info(f"  [SCHED] Programado: {hora}")

    log.info(f"\n  Total: {len(horarios_unicos)} actualizaciones/dia")
    log.info("  Presiona Ctrl+C para detener.\n")

    run_update()

    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    start_scheduler()
