from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    openai_api_key: str
    serper_api_key: str
    openai_model: str = "gpt-4.1-mini"

    # Telegram MTProto (Telethon)
    telegram_api_id: int = 0
    telegram_api_hash: str = ""
    telegram_session: str = ""   # StringSession — генерируется скриптом scripts/gen_tg_session.py

    # TGStat API (https://tgstat.ru/developers)
    tgstat_token: str = ""

    # YouTube Data API v3
    youtube_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
