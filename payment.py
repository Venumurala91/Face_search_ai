# payment.py

import time
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel , EmailStr
from sqlalchemy.orm import Session

import database as db

# --- CHANGE: Import the dependency from the new file ---
from dependencies import get_current_guest

# --- Pydantic model for this router ---
class DownloadRequest(BaseModel):
    image_paths: List[str]
class EmailRequest(DownloadRequest):
    email: EmailStr


# --- Router Setup ---
router = APIRouter(
    prefix="/api",
    tags=["Payment"],
)

# --- In-memory dictionary to track payment sessions ---
payment_sessions = {}

# --- Helper function for post-payment actions ---
def log_download_and_notify_admin(guest: db.Guest, image_paths: List[str], db_session: Session):
    """Logs the order and triggers admin notifications."""
    db.log_activity(
        db_session,
        guest_id=guest.id,
        action="PAYMENT_CONFIRMED",
        details=f"Confirmed payment for {len(image_paths)} photos."
    )
    new_download_log = db.DownloadLog(
        guest_id=guest.id,
        image_paths=",".join(image_paths)
    )
    db_session.add(new_download_log)
    db_session.commit()
    # Placeholder for email sending
    # send_email_to_admin(guest.name, guest.mobile_number, image_paths)

# --- Payment API Endpoints ---
@router.post("/start-payment")
async def api_start_payment(request: DownloadRequest):
    """
    Initiates a new payment session and returns a unique transaction ID.
    """
    transaction_id = str(uuid.uuid4())
    payment_sessions[transaction_id] = {
        "status": "PENDING",
        "image_paths": request.image_paths,
        "created_at": time.time(),
        "poll_count": 0  # For dummy confirmation
    }
    return {"transaction_id": transaction_id}


@router.get("/check-payment-status/{transaction_id}")
async def api_check_payment_status(
    transaction_id: str,
    guest: db.Guest = Depends(get_current_guest), # This now works correctly
    db_session: Session = Depends(db.get_db)
):
    """
    Polls for the status of a payment session.
    Simulates payment confirmation after a few polls.
    """
    session = payment_sessions.get(transaction_id)
    if not session:
        raise HTTPException(status_code=404, detail="Payment session not found or expired.")

    # --- DUMMY PAYMENT CONFIRMATION LOGIC ---
    session["poll_count"] += 1
    if session["status"] == "PENDING" and session["poll_count"] >= 4:
        session["status"] = "PAID"
        log_download_and_notify_admin(guest, session["image_paths"], db_session)

    if time.time() - session["created_at"] > 600:
        if transaction_id in payment_sessions:
            del payment_sessions[transaction_id]
        raise HTTPException(status_code=408, detail="Payment session timed out.")

    return {"status": session["status"]}