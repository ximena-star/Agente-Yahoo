# -*- coding: utf-8 -*-
"""
Configuracion — Stock Agent
INSTRUCCIONES:
1. Copia este archivo y renombralo a config.py
2. Rellena cada campo con tus datos reales
3. NUNCA subas config.py a GitHub (ya esta en .gitignore)
"""

CONFIG = {
    # ── Groq (GRATIS) ─────────────────────────────────────────────────────────
    # Obtén tu key GRATIS en: https://console.groq.com → API Keys
    "GROQ_API_KEY": "gsk_TU_KEY_AQUI",

    # ── Email de envio ────────────────────────────────────────────────────────
    # Correo Gmail desde donde se envia
    "EMAIL_FROM":    "tu_correo@gmail.com",
    # Correo donde quieres recibir las actualizaciones
    "EMAIL_TO":      "correo_destino@gmail.com",
    # Contraseña de aplicacion Gmail (no tu contraseña normal)
    # Guia: myaccount.google.com > Seguridad > Contraseñas de aplicacion
    "SMTP_PASSWORD": "xxxx xxxx xxxx xxxx",

    # ── Servidor SMTP ─────────────────────────────────────────────────────────
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": 465,
}
