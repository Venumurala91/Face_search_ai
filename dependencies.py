# dependencies.py

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

import database as db

# ===================================================================
# GUEST DEPENDENCIES
# ===================================================================

def get_current_guest(request: Request, db_session: Session = Depends(db.get_db)):
    """
    FastAPI dependency for HTML pages that require a guest to be logged in.
    If the guest is not authenticated, this will redirect them to the guest login page.
    """
    guest_id = request.cookies.get("guest_session")
    if guest_id and guest_id.isdigit():
        guest = db_session.query(db.Guest).filter(db.Guest.id == int(guest_id)).first()
        if guest:
            return guest
    # For pages, a redirect is the expected behavior for an unauthenticated user.
    raise HTTPException(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        detail="Not authenticated, redirecting to login.",
        headers={"Location": "/"},
    )

def get_current_guest_api(request: Request, db_session: Session = Depends(db.get_db)):
    """
    FastAPI dependency for API endpoints that require a guest to be logged in.
    If the guest is not authenticated, this will raise a 401 Unauthorized error.
    """
    guest_id = request.cookies.get("guest_session")
    if guest_id and guest_id.isdigit():
        guest = db_session.query(db.Guest).filter(db.Guest.id == int(guest_id)).first()
        if guest:
            return guest
    # For APIs, a 401 error is the correct response for an unauthenticated user.
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated for API access",
        headers={"WWW-Authenticate": "Bearer"},
    )

# ===================================================================
# ADMIN DEPENDENCIES
# ===================================================================

def get_current_admin(request: Request, db_session: Session = Depends(db.get_db)):
    """
    FastAPI dependency for HTML pages that require an admin to be logged in.
    If the admin is not authenticated, this will redirect them to the admin login page.
    """
    admin_id = request.cookies.get("admin_session")
    if admin_id and admin_id.isdigit():
        admin = db_session.query(db.Admin).filter(db.Admin.id == int(admin_id)).first()
        if admin:
            return admin
    raise HTTPException(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        detail="Not authenticated, redirecting to admin login.",
        headers={"Location": "/admin/login"},
    )

def get_current_admin_api(request: Request, db_session: Session = Depends(db.get_db)):
    """
    FastAPI dependency for API endpoints that require an admin to be logged in.
    If the admin is not authenticated, this will raise a 401 Unauthorized error.
    """
    admin_id = request.cookies.get("admin_session")
    if admin_id and admin_id.isdigit():
        admin = db_session.query(db.Admin).filter(db.Admin.id == int(admin_id)).first()
        if admin:
            return admin
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Admin not authenticated for API access",
        headers={"WWW-Authenticate": "Bearer"},
    )