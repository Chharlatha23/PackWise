import urllib.parse
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx

from app.core.config import settings
from app.core.database import get_user_db
from app.models.user import User
from app.schemas.auth import (
    TokenResponse,
    UserResponse,
    OAuthUrlResponse,
    TokenExchangeRequest,
    UserRegisterRequest,
    UserLoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest
)
from app.services.auth_service import (
    generate_oauth_state,
    verify_oauth_state,
    create_access_token,
    get_or_create_google_user,
    register_user,
    authenticate_user,
    create_password_reset_token,
    reset_password_with_token
)
from app.api.auth_deps import get_current_user

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


@auth_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, summary="Register a new user")
def register(payload: UserRegisterRequest, db: Session = Depends(get_user_db)):
    """Registers a new user, hashes password, triggers welcome email, and returns JWT token."""
    try:
        user = register_user(db, name=payload.name, email=payload.email, password=payload.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    access_token = create_access_token({"sub": user.id, "email": user.email, "name": user.name})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@auth_router.post("/login", response_model=TokenResponse, summary="Log in with email and password")
def login(payload: UserLoginRequest, db: Session = Depends(get_user_db)):
    """Authenticates an existing user and returns JWT access token."""
    user = authenticate_user(db, email=payload.email, password=payload.password)
    if not user:
        # Check if email exists at all to provide helpful guidance without revealing sensitive info
        existing = db.query(User).filter(User.email == payload.email.strip().lower()).first()
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No account found with this email. Please sign up first."
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password. Please try again or use forgot password."
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated.")

    access_token = create_access_token({"sub": user.id, "email": user.email, "name": user.name})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@auth_router.post("/forgot-password", summary="Request password reset link")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_user_db)):
    """
    Initiates password reset flow. Sends email if registered.
    Always returns uniform success message to prevent user enumeration.
    """
    create_password_reset_token(db, payload.email)
    return {
        "message": "If an account exists with this email address, a password reset link has been dispatched.",
        "status": "ok"
    }


@auth_router.post("/reset-password", summary="Reset password using token")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_user_db)):
    """Validates single-use reset token and updates user password."""
    success = reset_password_with_token(db, payload.token, payload.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or already used password reset link."
        )
    return {
        "message": "Your password has been successfully reset. You may now log in.",
        "status": "ok"
    }


@auth_router.get("/google/login", response_model=OAuthUrlResponse, summary="Get Google OAuth Authorization URL")
def google_login():
    """Generates a secure state and returns the Google OAuth authorization URL for frontend redirection."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured on the server (GOOGLE_CLIENT_ID missing)."
        )

    state = generate_oauth_state()
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "state": state,
        "prompt": "select_account"
    }
    url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return OAuthUrlResponse(authorization_url=url, state=state)


@auth_router.get("/google/redirect", summary="Direct browser redirect to Google OAuth")
def google_redirect():
    """Directly redirects browser to Google's OAuth consent screen."""
    url_resp = google_login()
    return RedirectResponse(url=url_resp.authorization_url)


@auth_router.get("/google/callback", summary="Google OAuth Callback Handler")
async def google_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_user_db)
):
    """
    Handles Google OAuth redirect:
    1. Validates state against CSRF attacks.
    2. Exchanges authorization code for tokens.
    3. Retrieves verified profile.
    4. Persists/updates user and issues signed JWT.
    5. Redirects user to frontend.
    """
    if error:
        frontend_err_url = f"{settings.FRONTEND_URL}/login?error={urllib.parse.quote(f'Google OAuth error: {error}')}"
        return RedirectResponse(url=frontend_err_url)

    if not code or not state:
        frontend_err_url = f"{settings.FRONTEND_URL}/login?error={urllib.parse.quote('Missing authorization code or state')}"
        return RedirectResponse(url=frontend_err_url)

    if not verify_oauth_state(state):
        frontend_err_url = f"{settings.FRONTEND_URL}/login?error={urllib.parse.quote('Invalid or expired OAuth state token (CSRF check failed)')}"
        return RedirectResponse(url=frontend_err_url)

    token_payload = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(GOOGLE_TOKEN_URL, data=token_payload)
            if token_resp.status_code != 200:
                err_text = token_resp.text
                frontend_err_url = f"{settings.FRONTEND_URL}/login?error={urllib.parse.quote(f'Failed to exchange authorization code: {err_text}')}"
                return RedirectResponse(url=frontend_err_url)
            
            tokens = token_resp.json()
            access_token = tokens.get("access_token")
            if not access_token:
                frontend_err_url = f"{settings.FRONTEND_URL}/login?error={urllib.parse.quote('Google token response missing access_token')}"
                return RedirectResponse(url=frontend_err_url)

            userinfo_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if userinfo_resp.status_code != 200:
                frontend_err_url = f"{settings.FRONTEND_URL}/login?error={urllib.parse.quote('Failed to fetch user profile from Google')}"
                return RedirectResponse(url=frontend_err_url)
            
            profile = userinfo_resp.json()
    except Exception as e:
        frontend_err_url = f"{settings.FRONTEND_URL}/login?error={urllib.parse.quote(f'Network error communicating with Google: {str(e)}')}"
        return RedirectResponse(url=frontend_err_url)

    google_id = profile.get("sub")
    email = profile.get("email")
    email_verified = profile.get("email_verified", False)
    name = profile.get("name")
    picture = profile.get("picture")

    if not google_id or not email:
        frontend_err_url = f"{settings.FRONTEND_URL}/login?error={urllib.parse.quote('Google profile did not contain required email or ID')}"
        return RedirectResponse(url=frontend_err_url)

    if not email_verified:
        frontend_err_url = f"{settings.FRONTEND_URL}/login?error={urllib.parse.quote('Google email is not verified')}"
        return RedirectResponse(url=frontend_err_url)

    user, _ = get_or_create_google_user(db, google_id=google_id, email=email, name=name, picture=picture)
    app_token = create_access_token({"sub": user.id, "email": user.email, "name": user.name})

    frontend_success_url = f"{settings.FRONTEND_URL}/login?token={app_token}"
    return RedirectResponse(url=frontend_success_url)


@auth_router.post("/google/token", summary="Direct code-for-token exchange endpoint")
async def exchange_google_token(
    payload: TokenExchangeRequest,
    db: Session = Depends(get_user_db)
):
    """
    Exchanges authorization code directly for PackWise JWT.
    Used when Google redirects directly to frontend (e.g. http://localhost:5173/login?code=...).
    """
    if payload.state and not verify_oauth_state(payload.state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state token (CSRF check failed)"
        )

    token_payload = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": payload.code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(GOOGLE_TOKEN_URL, data=token_payload)
            if token_resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to exchange authorization code with Google: {token_resp.text}"
                )
            
            tokens = token_resp.json()
            access_token = tokens.get("access_token")
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Google token response missing access_token"
                )

            userinfo_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if userinfo_resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to retrieve user profile from Google"
                )
            profile = userinfo_resp.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Network error communicating with Google: {str(e)}"
        )

    google_id = profile.get("sub")
    email = profile.get("email")
    email_verified = profile.get("email_verified", False)
    name = profile.get("name")
    picture = profile.get("picture")

    if not google_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google profile did not contain required email or ID"
        )

    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google email is not verified"
        )

    user, _ = get_or_create_google_user(db, google_id=google_id, email=email, name=name, picture=picture)
    app_token = create_access_token({"sub": user.id, "email": user.email, "name": user.name})

    return {
        "access_token": app_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login
        }
    }


@auth_router.get("/me", response_model=UserResponse, summary="Get Current Authenticated User")
def get_me(current_user: User = Depends(get_current_user)):
    """Returns the profile of the currently logged-in user."""
    return current_user


@auth_router.post("/logout", summary="Log Out Current User")
def logout(response: Response, current_user: User = Depends(get_current_user)):
    """Terminates session on server/client."""
    return {"message": "Successfully logged out.", "status": "ok"}
