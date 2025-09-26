
# Face_search_logic_milvus.py

import numpy as np
import cv2
import os
import insightface
from insightface.app import FaceAnalysis
from pymilvus import (connections, utility, FieldSchema, CollectionSchema, DataType, Collection)
from dotenv import load_dotenv

load_dotenv()

# --- GLOBAL CONFIGURATION ---
MILVUS_HOST = os.getenv("MILVUS_HOST", "127.0.0.1")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MODEL_NAME = os.getenv("MODEL_NAME", "buffalo_l")
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", 512))
METRIC_TYPE = os.getenv("METRIC_TYPE", "L2")
DISTANCE_THRESHOLD = float(os.getenv("DISTANCE_THRESHOLD", 1.0))
NPROBE = int(os.getenv("NPROBE", 20))

# --- PREVIEW IMAGE CONFIGURATION ---
PREVIEW_IMAGE_DIR = "images_preview"
WATERMARK_TEXT = "Your Park Memories"


# --- TARGET SIZE CONFIGURATION ---
TARGET_PREVIEW_SIZE_KB = 30  # The goal file size in kilobytes
TARGET_SIZE_TOLERANCE_KB = 25# How close we need to get (e.g., 15-25 KB is acceptable)
MAX_ITERATIONS = 10          # Safety limit to prevent infinite loops

# --- SINGLETON MODEL LOADER ---
APP_MODEL_INSTANCE = None

def get_model():
    """Singleton pattern to ensure the InsightFace model is loaded only once."""
    global APP_MODEL_INSTANCE
    if APP_MODEL_INSTANCE is None:
        print("Initializing InsightFace model for the first time...")
        APP_MODEL_INSTANCE = FaceAnalysis(name=MODEL_NAME, allowed_modules=['detection', 'recognition'])
        APP_MODEL_INSTANCE.prepare(ctx_id=-1, det_size=(1024, 1024))
        print("InsightFace model loaded successfully.")
    return APP_MODEL_INSTANCE

# --- SMART SAVE FUNCTION ---
def save_image_to_target_size(cv_image, output_path: str):
    """
    Iteratively saves a CV2 image to get as close as possible to the target file size.
    Uses a binary search on the JPEG quality setting for efficiency.
    """
    low_quality = 0
    high_quality = 100
    best_quality = 50 # Start in the middle
    
    # Binary search to find the best quality setting
    for _ in range(MAX_ITERATIONS):
        current_quality = (low_quality + high_quality) // 2
        print(f"Current quality of image {current_quality}")
        # Prevent quality from being 0 which can cause issues
        if current_quality == 0: current_quality = 1


        result, buffer = cv2.imencode('.jpg', cv_image, [cv2.IMWRITE_JPEG_QUALITY, current_quality])
        
        if not result:
            cv2.imwrite(output_path, cv_image, [cv2.IMWRITE_JPEG_QUALITY, 25])
            return

        current_size_kb = len(buffer) / 1024
        print(f"current_size {current_size_kb}")

        if abs(current_size_kb - TARGET_PREVIEW_SIZE_KB) <= TARGET_SIZE_TOLERANCE_KB:
            best_quality = current_quality
            break
        elif current_size_kb > TARGET_PREVIEW_SIZE_KB:
            high_quality = current_quality - 1
        else:
            low_quality = current_quality + 1
        
        best_quality = current_quality

    cv2.imwrite(output_path, cv_image, [cv2.IMWRITE_JPEG_QUALITY, best_quality])
    final_size = os.path.getsize(output_path) / 1024
    print(f"Saved {os.path.basename(output_path)} with quality {best_quality} -> {final_size:.2f} KB (Target: {TARGET_PREVIEW_SIZE_KB} KB)")

# --- REUSABLE PREVIEW GENERATION ---
# --- REPLACE THE OLD FUNCTION WITH THIS ONE ---
def create_preview_image(original_path: str, collection_name: str):
    """
    Creates a watermarked, web-optimized preview image and saves it
    into a subdirectory named after its collection.
    """
    if not os.path.exists(original_path):
        return None

    # CHANGE 1: Construct the new path with the collection name as a subfolder
    preview_path = os.path.join(PREVIEW_IMAGE_DIR, collection_name, os.path.basename(original_path))

    if os.path.exists(preview_path):
        return preview_path
    try:
        img = cv2.imread(original_path)
        if img is None:
            return None
        preview_img = img.copy()
        (h, w) = preview_img.shape[:2]
        font_scale = max(1, h / 700)
        thickness = max(1, int(h / 300))
        cv2.putText(preview_img, WATERMARK_TEXT, (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255, 128), thickness, cv2.LINE_AA)

        # CHANGE 2: Ensure the subdirectory exists before saving the file
        os.makedirs(os.path.dirname(preview_path), exist_ok=True)
        
        save_image_to_target_size(preview_img, preview_path)
        return preview_path
    except Exception as e:
        print(f"Error creating instant preview for {original_path}: {e}")
        return None

# --- CORE LOGIC CLASS ---
class FaceSearchEngine:
    """Manages face search logic and Milvus collection interactions."""

    def __init__(self, collection_name: str):
        if not collection_name: raise ValueError("Collection name must be provided.")
        self.collection_name = collection_name
        self.app_model = get_model()
        self.collection = None

    def connect_to_milvus(self):
        if not connections.has_connection("default"):
            connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)

    def load_or_create_index(self):
        self.connect_to_milvus()
        if not utility.has_collection(self.collection_name):
            fields = [
                FieldSchema(name="pk_id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="image_path", dtype=DataType.VARCHAR, max_length=1024),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIMENSION)
            ]
            schema = CollectionSchema(fields, f"Face search collection: {self.collection_name}")
            self.collection = Collection(name=self.collection_name, schema=schema)
            index_params = {"metric_type": METRIC_TYPE, "index_type": "IVF_FLAT", "params": {"nlist": 1024}}
            self.collection.create_index(field_name="embedding", index_params=index_params)
        else:
            self.collection = Collection(name=self.collection_name)
        self.collection.load()

    def search_person(self, query_image_np, top_k=100):
        if self.collection is None: self.load_or_create_index()
        faces = self.app_model.get(query_image_np)
        if not faces: return {"status": "No faces detected in the uploaded image.", "results": []}
        query_embeddings = [face.normed_embedding for face in faces]
        search_params = {"metric_type": METRIC_TYPE, "params": {"nprobe": NPROBE}}
        list_of_results = self.collection.search(data=query_embeddings, anns_field="embedding", param=search_params, limit=top_k, output_fields=["image_path"])
        all_hits = []
        for hits_for_one_face in list_of_results:
            for hit in hits_for_one_face:
                if hit.distance < DISTANCE_THRESHOLD:
                    all_hits.append({"image_path": hit.entity.get("image_path"), "distance": hit.distance})
        if not all_hits: return {"status": f"Detected {len(faces)} face(s), but no confident matches found.", "results": []}
        best_hits = {}
        for hit in all_hits:
            path = hit["image_path"]
            if path not in best_hits or hit["distance"] < best_hits[path]["distance"]:
                best_hits[path] = hit
        final_results = sorted(list(best_hits.values()), key=lambda x: x['distance'])
        status_msg = f"Search complete. Found {len(final_results)} potential matches."
        return {"status": status_msg, "results": final_results}

    # --- REPLACE your existing 'add_images_from_directory' function with this complete code ---

    def add_images_from_directory(self, image_directory: str):
        try:
            # --- Load the collection at the start of the operation ---
            self.load_or_create_index()
            
            # Get a list of image paths already processed and stored in Milvus
            res = self.collection.query(expr="", output_fields=["image_path"], limit=16384)
            processed_paths = {os.path.normpath(item['image_path']).lower() for item in res}
            
            # Get a list of all valid image files currently on the disk
            all_disk_images = [os.path.normpath(os.path.join(image_directory, f)) for f in os.listdir(image_directory) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
            # Determine which images are new and need to be processed
            new_images = [p for p in all_disk_images if p.lower() not in processed_paths]
            
            if not new_images:
                return {"status": "Collection is already up-to-date.", "images_added": 0, "faces_added": 0}
            
            image_path_list, embedding_list, images_processed_count = [], [], 0
            print(f"Processing {len(new_images)} new images from '{image_directory}'...")
            
            # Loop through only the new images
            for img_path in new_images:
                try:
                    # ================================================================= #
                    # THE ONLY CHANGE IS ON THE NEXT LINE:
                    # We now pass `self.collection_name` to create_preview_image
                    # so it knows which subfolder to save the preview in.
                    create_preview_image(img_path, self.collection_name)
                    # ================================================================= #
                    
                    img = cv2.imread(img_path)
                    if img is None:
                        print(f"Warning: Could not read image {img_path}")
                        continue
                        
                    faces = self.app_model.get(img)
                    if not faces:
                        continue
                        
                    images_processed_count += 1
                    for face in faces:
                        image_path_list.append(img_path)
                        embedding_list.append(face.normed_embedding)
                        
                except Exception as e:
                    print(f"Error processing {img_path}: {e}")
            
            if not embedding_list:
                return {"status": "New images found, but no new faces could be extracted.", "images_added": images_processed_count, "faces_added": 0}
            
            # Insert the new data into the Milvus collection
            self.collection.insert([image_path_list, embedding_list])
            self.collection.flush()
            
            return {"status": f"Successfully added new faces to '{self.collection_name}'.", "images_added": images_processed_count, "faces_added": len(embedding_list)}

        finally:
            # --- Always release the collection when the operation is done ---
            if self.collection:
                self.collection.release()
                print(f"--- Released collection: {self.collection_name} ---")

    def sync_directory(self, image_directory: str):
        if self.collection is None: self.load_or_create_index()
        if not os.path.exists(image_directory): return {"status": "error", "message": f"Source directory '{image_directory}' not found."}
        res = self.collection.query(expr="", output_fields=["image_path"], limit=16384)
        paths_in_milvus = {os.path.normpath(item['image_path']) for item in res}
        paths_on_disk = {os.path.normpath(os.path.join(image_directory, f)) for f in os.listdir(image_directory) if f.lower().endswith(('.png', '.jpg', '.jpeg'))}
        stale_paths = list(paths_in_milvus - paths_on_disk)
        if not stale_paths: return {"status": "success", "message": "Collection is already in sync.", "removed_count": 0}
        expr = f'image_path in {stale_paths}'
        try:
            self.collection.delete(expr)
            self.collection.flush()
            for path in stale_paths:
                preview_file = os.path.join(PREVIEW_IMAGE_DIR, os.path.basename(path))
                if os.path.exists(preview_file): os.remove(preview_file)
            return {"status": "success", "message": f"Successfully removed {len(stale_paths)} stale entries.", "removed_count": len(stale_paths)}
        except Exception as e:
            return {"status": "error", "message": f"An error occurred during deletion: {e}", "removed_count": 0}