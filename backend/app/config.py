import os


class Settings:
    app_name: str = "SkillSetu AI"
    api_prefix: str = "/api"
    db_url: str = os.getenv("SKILLSETU_DB_URL", "sqlite:///./skillsetu.db")
    secret_key: str = "skillsetu-demo-secret-key"
    integration_api_key: str = "skillsetu-demo-api-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24


settings = Settings()
