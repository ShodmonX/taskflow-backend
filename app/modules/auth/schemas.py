from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """
    Schema for user registration requests.

    Attributes:
        email (EmailStr): The user's email address. Must be a valid email format.
        username (str): The desired username. Must be between 3 and 50 characters.
        password (str): The user's password. Must be between 8 and 128 characters.
    """
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """
    Schema for user login request.

    Attributes:
        email (EmailStr): The user's email address.
        password (str): The user's password.
    """
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """
        Schema for token response.

        Attributes:
            access_token (str): The JWT access token.
            token_type (str): The type of the token, typically "bearer".
    """
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    """
    Schema representing the response for the current authenticated user.

    Attributes:
        id (str): Unique identifier of the user.
        email (EmailStr): Email address of the user.
        username (str): Username of the user.
        is_active (bool): Indicates if the user's account is active.
        is_verified (bool): Indicates if the user's email is verified.
        is_superuser (bool): Indicates if the user has superuser privileges.
    """
    id: str
    email: EmailStr
    username: str
    is_active: bool
    is_verified: bool
    is_superuser: bool
