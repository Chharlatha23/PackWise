import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Tuple
import bcrypt
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.user import User, PasswordReset
from app.services.email_service import send_welcome_email, send_password_reset_email

# In-memory transient state cache for CSRF protection during OAuth authorization code flow
_OAUTH_STATES: Dict[str, datetime] = {}

def hash_password(password: str) -> str:
    """Hash password securely using bcrypt."""
    pw_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def generate_oauth_state() -> str:
    """Generate and record a secure random CSRF state token."""
    state = secrets.token_urlsafe(32)
    # Prune expired states (> 15 minutes)
    now = datetime.now(timezone.utc)
    expired = [k for k, exp in _OAUTH_STATES.items() if (now - exp).total_seconds() > 900]
    for k in expired:
        _OAUTH_STATES.pop(k, None)
    _OAUTH_STATES[state] = now
    return state

def verify_oauth_state(state: str) -> bool:
    """Verify that the state returned from Google matches an active session state."""
    if not state or state not in _OAUTH_STATES:
        return False
    state_time = _OAUTH_STATES.pop(state)
    return (datetime.now(timezone.utc) - state_time).total_seconds() <= 900

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    if "sub" in to_encode and to_encode["sub"] is not None:
        to_encode["sub"] = str(to_encode["sub"])
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a signed JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

def register_user(db: Session, name: str, email: str, password: str) -> User:
    """Register a new user with email and password, hashing password and sending welcome email."""
    normalized_email = email.strip().lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise ValueError("An account with this email address already exists.")

    pw_hash = hash_password(password)
    now = datetime.now(timezone.utc)

    user = User(
        email=normalized_email,
        name=name.strip(),
        password_hash=pw_hash,
        auth_provider="email",
        role_id=2,
        is_active=True,
        created_at=now,
        last_login=now
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Trigger welcome email once upon account creation (fails safely without disrupting registration)
    send_welcome_email(user.email, user.name or "")

    return user

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate existing user by email and password."""
    normalized_email = email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user:
        return None
    if not user.password_hash or not verify_password(password, user.password_hash):
        return None

    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user

def get_or_create_google_user(
    db: Session,
    google_id: str,
    email: str,
    name: Optional[str] = None,
    picture: Optional[str] = None
) -> Tuple[User, bool]:
    """
    Retrieve existing user by google_id or email, or create new user record.
    Returns (user, is_new_account).
    """
    normalized_email = email.strip().lower()
    user = db.query(User).filter((User.google_id == google_id) | (User.email == normalized_email)).first()
    now = datetime.now(timezone.utc)
    if user:
        user.last_login = now
        if google_id and not user.google_id:
            user.google_id = google_id
        if name and not user.name:
            user.name = name
        if picture and not user.picture:
            user.picture = picture
        db.commit()
        db.refresh(user)
        return user, False
    
    new_user = User(
        email=normalized_email,
        name=name,
        picture=picture,
        google_id=google_id,
        role_id=2,
        auth_provider="google",
        is_active=True,
        created_at=now,
        last_login=now
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Send welcome email only once when account is newly created via Google
    send_welcome_email(new_user.email, new_user.name or "")

    return new_user, True

def create_password_reset_token(db: Session, email: str) -> Optional[str]:
    """Generates and saves a secure single-use password reset token for the email if account exists."""
    normalized_email = email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user:
        return None

    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

    # Invalidate any existing unused reset tokens for this user
    db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.used_at.is_(None)
    ).update({"used_at": datetime.now(timezone.utc)})

    reset_record = PasswordReset(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        created_at=datetime.now(timezone.utc)
    )
    db.add(reset_record)
    db.commit()

    # Send reset email
    send_password_reset_email(user.email, raw_token, user.name)

    return raw_token

def reset_password_with_token(db: Session, raw_token: str, new_password: str) -> bool:
    """Validates single-use reset token and updates the user's password."""
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)

    reset_record = db.query(PasswordReset).filter(
        PasswordReset.token_hash == token_hash,
        PasswordReset.used_at.is_(None),
        PasswordReset.expires_at > now
    ).first()

    if not reset_record:
        return False

    user = db.query(User).filter(User.id == reset_record.user_id).first()
    if not user:
        return False

    # Update password and mark token as used
    user.password_hash = hash_password(new_password)
    user.updated_at = now
    reset_record.used_at = now
    db.commit()
    return True
