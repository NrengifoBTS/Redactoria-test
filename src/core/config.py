#redactoria-test/src/core/config.py

"""
Core configuration settings.

Centralizes configuration that was previously duplicated across services.
"""
import os


class Settings:
    """
    Centralized settings for the application.

    Los roles (admin/editor/redactor/master) viven en la BD (columna users.role),
    no aquí. Ver src.auth.roles y src.auth.permissions.
    """

    # NOTA: La determinación de quién es admin/redactor vive en la BD
    # (columna users.role). Usa src.auth.permissions.get_admin_user_ids(db)
    # / is_admin_user(db, user_id) en lugar de listas hardcodeadas.

    # Notification settings
    # 1. Leemos el Webhook (en test puede estar vacío en el .env.test)
    TEAMS_WEBHOOK_URL: str = os.getenv("TEAMS_WEBHOOK_URL", "")
    
    # 2. IMPORTANTE: El valor por defecto en test será sobreescrito por el .env.test (http://192.168.1.129:3001)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3001")
    
    # 3. Notificaciones: os.getenv devolverá lo que diga tu .env.test
    ENABLE_TEAMS_NOTIFICATIONS: bool = os.getenv("ENABLE_TEAMS_NOTIFICATIONS", "true").lower() == "true"
    
    # 4. Nombre del Bot: Cámbialo en el .env.test para saber qué instancia te escribe
    TEAMS_BOT_NAME: str = os.getenv("TEAMS_BOT_NAME", "Sistema de Notificaciones")

    TIMEZONE: str = os.getenv("TIMEZONE", "America/Bogota")

# Singleton instance
settings = Settings()