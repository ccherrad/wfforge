from fastapi import HTTPException, status, Header
from .config import settings


async def verify_api_key(api_key: str = Header(None)):
    """Verify API key from header"""
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return api_key