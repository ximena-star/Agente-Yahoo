# -*- coding: utf-8 -*-
"""
Configuracion — Stock Agent
IMPORTANTE: Renombra este archivo a config.py y rellena con tus datos reales.
NO subas config.py a GitHub — ya esta en .gitignore
"""

CONFIG = {
    # ── Groq (GRATIS) ─────────────────────────────────────────────────────────
    # Obtén tu key GRATIS en: https://console.groq.com → API Keys
    "GROQ_API_KEY": "gsk_TU_KEY_AQUI",

    # ── Email de envio ────────────────────────────────────────────────────────
    "EMAIL_FROM":    "tu_correo@gmail.com",       # correo Gmail que envia
    "EMAIL_TO":      ["destino1@gmail.com",        # lista de correos destino
                      "destino2@gmail.com"],        # agrega o quita correos aqui
    "SMTP_PASSWORD": "xxxx xxxx xxxx xxxx",        # contraseña de app Gmail (16 chars)

    # ── Servidor SMTP Gmail ───────────────────────────────────────────────────
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": 465,
}
