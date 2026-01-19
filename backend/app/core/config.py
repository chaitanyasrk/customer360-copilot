"""
Application configuration using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Salesforce Configuration - Method 1: Username/Password/Token
    SALESFORCE_USERNAME: str = ""
    SALESFORCE_PASSWORD: str = ""
    SALESFORCE_SECURITY_TOKEN: str = ""
    
    # Salesforce Configuration - Method 2: OAuth 2.0 (Recommended)
    SALESFORCE_CLIENT_ID: str = ""
    SALESFORCE_CLIENT_SECRET: str = ""
    
    # Common Salesforce Settings
    SALESFORCE_DOMAIN: str = "login"  # 'login' for production, 'test' for sandbox
    SALESFORCE_VERIFY_SSL: bool = True  # Set to False to disable SSL verification (for corporate proxies)
    
    # Google Gemini API
    GOOGLE_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.0-flash"  # Model to use (e.g., gemini-2.0-flash, gemini-1.5-pro)
    
    # Batch Processing Configuration
    PARALLEL_BATCHES: bool = False  # If True, process batches in parallel (requires higher API quota)
    BATCH_DELAY_SECONDS: float = 2.0  # Delay between sequential batch calls to avoid rate limits
    
    # JWT Configuration
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Application Configuration
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    # Vector DB Configuration
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    
    # Custom Object Configuration for Summary Storage
    SUMMARY_OBJECT_API_NAME: str = "Case_Summary__c"  # API name of custom object
    SUMMARY_FIELD_NAME: str = "Summary__c"  # Field for storing the summary
    CASE_ID_FIELD_NAME: str = "Case__c"  # Lookup field to Case
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
