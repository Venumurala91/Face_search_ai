# main_milvus.py

# --- Standard Library Imports ---
import os
import io
import zipfile
import uvicorn
import datetime

# --- Third-Party Imports ---
import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request, Form,BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from pydantic import BaseModel
from pymilvus import utility
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

# --- Local Application Imports ---
import database as db
from dependencies import get_current_admin, get_current_guest, get_current_admin_api, get_current_guest_api
from Face_search_logic_milvus import FaceSearchEngine, PREVIEW_IMAGE_DIR
from payment import router as payment_router
from payment import DownloadRequest,EmailRequest
from email_utils import send_photos_email

# ===================================================================
# 1. CORE APPLICATION SETUP
# ===================================================================

# --- Configuration & App Initialization ---
BASE_IMAGE_DIRECTORY = "images"
app = FastAPI(title="FaceSearch AI System", version="4.8.0",
              description="An AI-powered system for theme parks to manage and sell guest photos using face recognition.")


@app.post("/api/send-email", tags=["Guest APIs"])
async def api_send_email(
    request: EmailRequest,
    background_tasks: BackgroundTasks,
    guest: db.Guest = Depends(get_current_guest_api),
    db_session: Session = Depends(db.get_db)
):
    """
    Sends the selected photos as a ZIP file to the user's email address.
    This runs as a background task to avoid blocking the API response.
    """
    if not request.image_paths:
        raise HTTPException(status_code=400, detail="No image paths provided.")

    db.log_activity(
        db_session,
        guest_id=guest.id,
        action="EMAIL_PHOTOS",
        details=f"Queued email with {len(request.image_paths)} photos to {request.email}"
    )

    background_tasks.add_task(
        send_photos_email,
        recipient_email=request.email,
        image_paths=request.image_paths,
        guest_name=guest.name
    )

    return JSONResponse(
        status_code=202, # Accepted
        content={"message": f"Your photos are on their way! An email is being sent to {request.email} and should arrive shortly."}
    )

# --- Geocoder Initialization ---
geolocator = Nominatim(user_agent="face_search_ai_app")
reverse = RateLimiter(geolocator.reverse, min_delay_seconds=1)

def get_address_from_coords(lat, lon):
    """Performs a reverse geocoding lookup to get a human-readable address."""
    if lat is None or lon is None: return "N/A"
    try:
        location = reverse((lat, lon), exactly_one=True, language='en')
        return location.address if location else f"Coords: {lat:.4f}, {lon:.4f}"
    except Exception as e:
        print(f"--- Geocoding Error: {e} ---")
        return f"Coords: {lat:.4f}, {lon:.4f}"

# --- FastAPI App Events (Startup & Shutdown) ---

@app.on_event("startup")
def startup_event():
    """Initializes database tables and connects to Milvus on startup."""
    db.create_db_and_tables()
    os.makedirs(BASE_IMAGE_DIRECTORY, exist_ok=True)
    os.makedirs(PREVIEW_IMAGE_DIR, exist_ok=True)
    os.makedirs("selected_images", exist_ok=True)
    with db.SessionLocal() as session:
        if not session.query(db.Admin).first():
            default_admin = db.Admin(username="admin", hashed_password=db.get_password_hash("admin123"))
            session.add(default_admin)
            session.commit()
            print("--- Startup: Default admin user 'admin' created. ---")
    utility.connections.connect("default", host=os.getenv("MILVUS_HOST", "127.0.0.1"), port=os.getenv("MILVUS_PORT", "19530"))
    print("--- Startup: Application startup complete. ---")

@app.on_event("shutdown")
def shutdown_event():
    """Disconnects from Milvus on shutdown."""
    utility.connections.disconnect("default")

# --- Static File and Asset Mounting ---
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.mount("/admin_static", StaticFiles(directory="admin_frontend/static"), name="admin_static")
app.mount("/images", StaticFiles(directory=BASE_IMAGE_DIRECTORY), name="images")
app.mount("/images_preview", StaticFiles(directory=PREVIEW_IMAGE_DIR), name="images_preview")

# --- Pydantic API Models ---
class UpdateRequest(BaseModel):
    source_directory: str; location: Optional[str] = None; latitude: float | None = None; longitude: float | None = None
class NewAdmin(BaseModel): username: str; password: str
class BulkDeleteRequest(BaseModel): ids: List[int]
class BulkDeleteNamesRequest(BaseModel): names: List[str]


# ===================================================================
# 2. API ROUTERS
# ===================================================================

# Include all payment-related endpoints from payment.py
app.include_router(payment_router)


# ===================================================================
# 3. PAGE SERVING ROUTES (HTML)
# ===================================================================

# --- Guest Pages ---
@app.get("/", response_class=HTMLResponse, tags=["Pages"])
async def serve_guest_login_page():
    """Serves the main login page for guests."""
    with open("frontend/login_index.html") as f:
        return HTMLResponse(content=f.read())

@app.get("/app", response_class=HTMLResponse, tags=["Pages"])
async def serve_main_app(guest: db.Guest = Depends(get_current_guest)):
    """Serves the main application page after a guest is authenticated."""
    with open("frontend/index.html") as f:
        return HTMLResponse(content=f.read())

# --- Admin Pages ---
@app.get("/admin/login", response_class=HTMLResponse, tags=["Pages"])
async def serve_admin_login_page():
    """Serves the login page for administrators."""
    with open("admin_frontend/login_index.html") as f:
        return HTMLResponse(content=f.read())

@app.get("/admin", response_class=HTMLResponse, tags=["Pages"])
async def serve_admin_dashboard(admin: db.Admin = Depends(get_current_admin)):
    """Serves the main admin dashboard page after an admin is authenticated."""
    with open("admin_frontend/admin_index.html") as f:
        return HTMLResponse(content=f.read())


# ===================================================================
# 4. API ENDPOINTS
# ===================================================================

# --- Authentication APIs ---
@app.post("/login", tags=["Authentication"])
async def guest_login(name: str = Form(...), mobile_number: str = Form(...), db_session: Session = Depends(db.get_db)):
    """Handles guest login, creates new guest if not found, and sets session cookie."""
    guest = db_session.query(db.Guest).filter(db.Guest.mobile_number == mobile_number).first()
    if not guest:
        guest = db.Guest(name=name, mobile_number=mobile_number)
        db_session.add(guest)
        db_session.commit()
    db.log_activity(db_session, guest_id=guest.id, action="GUEST_LOGIN")
    response = RedirectResponse(url="/app", status_code=303)
    response.set_cookie(key="guest_session", value=str(guest.id), httponly=True)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response
        
@app.post("/guest/logout", tags=["Authentication"])
async def guest_logout():
    """Logs out a guest by deleting their session cookie."""
    response = RedirectResponse(url="/")
    response.delete_cookie("guest_session")
    return response

@app.post("/admin/login", tags=["Authentication"])
async def admin_login(username: str = Form(...), password: str = Form(...), db_session: Session = Depends(db.get_db)):
    """Handles admin login and sets session cookie."""
    admin = db_session.query(db.Admin).filter(db.Admin.username == username).first()
    if not admin or not db.verify_password(password, admin.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(key="admin_session", value=str(admin.id), httponly=True)
    return response

@app.post("/admin/logout", tags=["Authentication"])
async def admin_logout():
    """Logs out an admin by deleting their session cookie."""
    response = RedirectResponse(url="/admin/login")
    response.delete_cookie("admin_session")
    return response

# --- Guest-Facing APIs ---
@app.get("/api/collections", tags=["Guest APIs"])
async def api_list_collections(guest: db.Guest = Depends(get_current_guest_api)):
    """Returns a list of all available collections for the guest to search in."""
    return {"collections": utility.list_collections()}

# --- REPLACE THE OLD 'api_search_face' FUNCTION WITH THIS ONE ---
@app.post("/api/search/{collection_name}", tags=["Guest APIs"])
async def api_search_face(collection_name: str, file: UploadFile = File(...), guest: db.Guest = Depends(get_current_guest_api), db_session: Session = Depends(db.get_db)):
    """Performs a face search in the specified collection for the guest."""
    db.log_activity(db_session, guest_id=guest.id, action="PERFORM_SEARCH", details=f"Searched in collection: {collection_name}")
    try:
        search_engine = FaceSearchEngine(collection_name=collection_name)
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        data = search_engine.search_person(img_np)
        
        corrected_results = []
        for result in data.get("results", []):
            original_path = result["image_path"]
            preview_filename = os.path.basename(original_path)
            
            # --- KEY CHANGE: The web path now includes the collection_name subfolder
            web_path = f"/{PREVIEW_IMAGE_DIR}/{collection_name}/{preview_filename}".replace('\\', '/')
            
            # Check if the file exists on disk using its full, correct path
            preview_path_on_disk = os.path.join(PREVIEW_IMAGE_DIR, collection_name, preview_filename)

            if os.path.exists(preview_path_on_disk):
                result["web_path"] = web_path
                result["original_path"] = original_path
                corrected_results.append(result)

        data["results"] = corrected_results
        if not corrected_results:
            data["status"] = "Search complete. No matches found."
        else:
            data["status"] = f"Search complete. Found {len(corrected_results)} potential matches."
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/download-selected/", tags=["Guest APIs"])
async def api_download_selected(request: DownloadRequest, guest: db.Guest = Depends(get_current_guest_api), db_session: Session = Depends(db.get_db)):
    """Creates and streams a ZIP file of the selected high-quality original images."""
    db.log_activity(db_session, guest_id=guest.id, action="DOWNLOAD_PHOTOS", details=f"Downloaded {len(request.image_paths)} photos.")
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, mode='w', compression=zipfile.ZIP_DEFLATED) as temp_zip:
        for original_path in request.image_paths:
            if os.path.exists(original_path):
                temp_zip.write(original_path, arcname=os.path.basename(original_path))
    zip_io.seek(0)
    return StreamingResponse(zip_io, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=FaceSearch_Memories.zip"})

# --- Admin-Only APIs ---
@app.get("/api/admin/collections", tags=["Admin APIs"])
async def api_get_collections_data(db_session: Session = Depends(db.get_db), admin: db.Admin = Depends(get_current_admin_api)):
    """Fetches detailed data for all collections for the admin dashboard."""
    collections_milvus = utility.list_collections()
    collection_logs = db_session.query(db.CollectionLog).all()
    log_map = {log.collection_name: log for log in collection_logs}
    collections_data = []
    for name in collections_milvus:
        embedding_count = "N/A"
        try:
            stats = utility.get_collection_stats(collection_name=name)
            embedding_count = next((stat.value for stat in stats if stat.key == 'row_count'), "N/A")
        except Exception:
            embedding_count = "Error"
        log_entry = log_map.get(name)
        total_images = 0
        if log_entry and log_entry.source_folder and os.path.isdir(log_entry.source_folder):
            total_images = len([f for f in os.listdir(log_entry.source_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
        collections_data.append({
            "name": name,
            "upload_datetime": log_entry.upload_datetime.strftime("%Y-%m-%d %H:%M") if log_entry else "N/A",
            "source_folder": log_entry.source_folder if log_entry else "N/A",
            "location": log_entry.location if log_entry else "N/A",
            "status": int(embedding_count) if str(embedding_count).isdigit() else embedding_count,
            "total_images": total_images,
        })
    return {"collections": collections_data}

@app.get("/api/admin/guests", tags=["Admin APIs"])
async def api_get_guests_data(db_session: Session = Depends(db.get_db), admin: db.Admin = Depends(get_current_admin_api)):
    guests = db_session.query(db.Guest).order_by(db.Guest.id.desc()).all()
    guests_data = [{"id": g.id, "name": g.name, "mobile_number": g.mobile_number, "created_at": g.created_at.strftime("%Y-%m-%d %H:%M:%S")} for g in guests]
    return {"guests": guests_data}

@app.get("/api/admin/activities", tags=["Admin APIs"])
async def api_get_activities_data(db_session: Session = Depends(db.get_db), admin: db.Admin = Depends(get_current_admin_api)):
    activities = db_session.query(db.ActivityLog).options(joinedload(db.ActivityLog.guest)).order_by(db.ActivityLog.timestamp.desc()).limit(200).all()
    activities_data = [{"id": a.id, "guest_name": a.guest.name if a.guest else "Deleted Guest", "action": a.action, "details": a.details, "timestamp": a.timestamp.strftime("%Y-%m-%d %H:%M:%S")} for a in activities]
    return {"activities": activities_data}

@app.get("/api/admin/admins", tags=["Admin APIs"])
async def api_get_admins_data(db_session: Session = Depends(db.get_db), admin: db.Admin = Depends(get_current_admin_api)):
    admins = db_session.query(db.Admin).all()
    return {"admins": admins}

@app.get("/api/admin/available-folders", tags=["Admin APIs"])
async def api_get_available_folders(admin: db.Admin = Depends(get_current_admin_api)):
    if not os.path.isdir(BASE_IMAGE_DIRECTORY): return {"folders": []}
    return {"folders": [item for item in os.listdir(BASE_IMAGE_DIRECTORY) if os.path.isdir(os.path.join(BASE_IMAGE_DIRECTORY, item))]}

@app.post("/api/admin/update-collection/{collection_name}", tags=["Admin APIs"])
async def api_update_collection(collection_name: str, request: UpdateRequest, db_session: Session = Depends(db.get_db), admin: db.Admin = Depends(get_current_admin_api)):
    """Creates a new collection or updates an existing one with new images."""
    engine = FaceSearchEngine(collection_name=collection_name)
    add_status = engine.add_images_from_directory(request.source_directory)
    if add_status.get("status") == "error":
        raise HTTPException(status_code=404, detail=add_status["message"])
    location_name = get_address_from_coords(request.latitude, request.longitude)
    log = db_session.query(db.CollectionLog).filter_by(collection_name=collection_name).first()
    if not log:
        log = db.CollectionLog(collection_name=collection_name, source_folder=request.source_directory, location=location_name, latitude=request.latitude, longitude=request.longitude)
        db_session.add(log)
    else:
        log.upload_datetime = datetime.datetime.now(datetime.UTC)
        log.location = location_name; log.latitude = request.latitude; log.longitude = request.longitude
    db_session.commit()
    return JSONResponse(content=add_status)

@app.post("/api/admin/sync-collection/{collection_name}", tags=["Admin APIs"])
async def api_sync_collection(collection_name: str, request: UpdateRequest, admin: db.Admin = Depends(get_current_admin_api)):
    engine = FaceSearchEngine(collection_name=collection_name)
    sync_status = engine.sync_directory(request.source_directory)
    if sync_status.get("status") == "error":
        raise HTTPException(status_code=404, detail=sync_status["message"])
    return JSONResponse(content=sync_status)

@app.delete("/api/admin/collections/bulk", tags=["Admin APIs"])
async def api_bulk_delete_collections(request: BulkDeleteNamesRequest, db_session: Session = Depends(db.get_db), admin: db.Admin = Depends(get_current_admin_api)):
    for name in request.names:
        if utility.has_collection(name):
            utility.drop_collection(name)
            log = db_session.query(db.CollectionLog).filter_by(collection_name=name).first()
            if log: db_session.delete(log)
    db_session.commit()
    return {"status": "success", "message": "Selected collections deleted."}

@app.delete("/api/admin/guests/bulk", tags=["Admin APIs"])
async def api_bulk_delete_guests(request: BulkDeleteRequest, db_session: Session = Depends(db.get_db), admin: db.Admin = Depends(get_current_admin_api)):
    db_session.query(db.Guest).filter(db.Guest.id.in_(request.ids)).delete(synchronize_session=False)
    db_session.commit()
    return {"status": "success", "message": "Selected guests deleted."}

@app.delete("/api/admin/activities/bulk", tags=["Admin APIs"])
async def api_bulk_delete_activities(request: BulkDeleteRequest, db_session: Session = Depends(db.get_db), admin: db.Admin = Depends(get_current_admin_api)):
    db_session.query(db.ActivityLog).filter(db.ActivityLog.id.in_(request.ids)).delete(synchronize_session=False)
    db_session.commit()
    return {"status": "success", "message": "Selected activities  deleted."}

@app.post("/api/admin/create-admin", tags=["Admin APIs"])
async def api_create_admin(new_admin_data: NewAdmin, db_session: Session = Depends(db.get_db), admin: db.Admin = Depends(get_current_admin_api)):
    if db_session.query(db.Admin).filter(db.Admin.username == new_admin_data.username).first():
        raise HTTPException(status_code=400, detail="Username already exists.")
    new_admin = db.Admin(username=new_admin_data.username, hashed_password=db.get_password_hash(new_admin_data.password))
    db_session.add(new_admin); db_session.commit()
    return {"status": "success", "message": f"Admin user '{new_admin_data.username}' created."}

@app.delete("/api/admin/admins/bulk", tags=["Admin APIs"])
async def api_bulk_delete_admins(request: BulkDeleteRequest, db_session: Session = Depends(db.get_db), current_admin: db.Admin = Depends(get_current_admin_api)):
    if current_admin.id in request.ids:
        raise HTTPException(status_code=400, detail="Bulk delete cannot include your own admin account.")
    db_session.query(db.Admin).filter(db.Admin.id.in_(request.ids)).delete(synchronize_session=False)
    db_session.commit()
    return {"status": "success", "message": "Selected admin users deleted."}

@app.post("/api/admin/login-as-guest/{guest_id}", tags=["Admin APIs"])
async def api_login_as_guest(guest_id: int, admin: db.Admin = Depends(get_current_admin_api), db_session: Session = Depends(db.get_db)):
    guest = db_session.query(db.Guest).filter(db.Guest.id == guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found.")
    response = JSONResponse(content={"redirect_url": "/app"})
    response.set_cookie(key="guest_session", value=str(guest.id), httponly=True)
    return response

# ===================================================================
# 5. MAIN APPLICATION RUNNER
# ===================================================================
if __name__ == "__main__":
    print("--- Starting FaceSearch AI Server ---")
    uvicorn.run("main_milvus:app", host="0.0.0.0", port=8000, reload=True)