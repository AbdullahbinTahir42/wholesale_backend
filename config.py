from dotenv import load_dotenv
import os

load_dotenv()  # Load .env file

class Settings:
    EMAIL_HOST: str = os.getenv("EMAIL_HOST")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", 587))
    EMAIL_USERNAME: str = os.getenv("EMAIL_USERNAME")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM")

settings = Settings()
