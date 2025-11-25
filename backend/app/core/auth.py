"""
JWT Authentication utilities
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.models.schemas import TokenPayload

security = HTTPBearer()


def create_access_token(subject: str, role: str) -> str:
    """
    Create a JWT access token
    
    Args:
        subject: User or agent identifier
        role: User role ("user" or "agent")
    
    Returns:
        Encoded JWT token
    """
    expire = datetime.utcnow() + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    
    to_encode = {
        "sub": subject,
        "exp": expire,
        "role": role
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> TokenPayload:
    """
    Verify JWT token and return payload
    
    Args:
        credentials: HTTP Authorization credentials
    
    Returns:
        Token payload
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        token_data = TokenPayload(
            sub=payload.get("sub"),
            exp=datetime.fromtimestamp(payload.get("exp")),
            role=payload.get("role")
        )
        
        if token_data.sub is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        return token_data
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


def verify_agent_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> TokenPayload:
    """
    Verify that the token belongs to an agent
    
    Args:
        credentials: HTTP Authorization credentials
    
    Returns:
        Token payload
    
    Raises:
        HTTPException: If token is invalid or not an agent token
    """
    token_data = verify_token(credentials)
    
    if token_data.role != "agent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent access required"
        )
    
    return token_data
