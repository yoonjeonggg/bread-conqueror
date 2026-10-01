from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    nickname: str = Field(min_length=2, max_length=30)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    # bcrypt only reads 72 bytes; the cap also keeps hashing cost bounded
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=2048)
