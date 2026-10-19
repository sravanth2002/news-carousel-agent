from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ig_user_id: str = ""
    ig_token: str = ""
    cloudinary_cloud: str = ""
    cloudinary_preset: str = ""
    out_dir: str = "output"
    num_slides: int = 10
    image_source: str = "auto"  # auto | article | commons | none
    import_to_photos: bool = False
    sync_dir: str = ""
    smtp_user: str = ""
    smtp_password: str = ""
    approver_email: str = ""
    approval_deadline_hour: int = 12


@lru_cache
def get_settings() -> Settings:
    return Settings()
