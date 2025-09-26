# Face_search_ai
🎡 Face Search AI – Theme Park Photo Search &amp; Management System  AI-powered guest photo experience for theme parks. Built with FastAPI + Milvus + InsightFace, it lets guests find and download their event photos using face recognition, while admins manage collections, users, and logs via a secure dashboard.




# FaceSearch AI - Setup and Installation Guide 

This document provides a complete step-by-step guide to set up and run the FaceSearch AI application using a clustered Milvus setup via Docker Compose.

### Table of Contents

1.  [Project Overview](#1-project-overview)
2.  [Technology Stack](#2-technology-stack)
3.  [Prerequisites](#3-prerequisites)
4.  [Step-by-Step Installation](#4-step-by-step-installation)
5.  [Running the Application](#5-running-the-application)
6.  [First-Time Admin Setup](#6-first-time-admin-setup)
7.  [Project Folder Structure](#7-project-folder-structure)

---

### 1. Project Overview

FaceSearch AI is a full-stack application that allows guests at an event or theme park to find their photos using facial recognition. It includes a guest-facing portal for searching and a secure admin dashboard for managing photo collections and system data.

---

### 2. Technology Stack

*   **Backend:** Python 3.10+, FastAPI
*   **AI/ML:**
    *   **Face Recognition:** `insightface`
    *   **Vector Database:** `Milvus 2.x` (Clustered, via Docker Compose)
*   **Database:** `MySQL` (for user and log data) - **Must be installed separately.**
*   **Frontend:** HTML5, CSS3, JavaScript, TailwindCSS
*   **Containerization:** Docker & Docker Compose

---

### 3. Prerequisites

Before you begin, ensure you have the following software installed on your system:

*   **Python** (version 3.10 or newer)
*   **Git**
*   **Docker** and **Docker Compose**
*   **MySQL Server:** You must install and run MySQL Server directly on your host machine, as it is **not** included in the Docker Compose setup.

---

### 4. Step-by-Step Installation

Follow these steps precisely to set up the project environment.

#### Step 1: Clone the Repository

Open your terminal and clone the project code from GitHub.

```bash
git clone <your-repository-url>
cd <repository-folder-name>
```

#### Step 2: Set Up Milvus with Docker Compose

This setup uses Docker to run the complete Milvus vector database stack.

1.  In the root of the project folder, create a file named `docker-compose.yml`.
2.  Copy and paste the following content into it:

    ```yml
    # docker-compose.yml

    services:
      etcd:
        container_name: milvus-etcd
        image: quay.io/coreos/etcd:v3.5.5
        environment:
          - ETCD_AUTO_COMPACTION_MODE=revision
          - ETCD_AUTO_COMPACTION_RETENTION=1000
          - ETCD_QUOTA_BACKEND_BYTES=4294967296
          - ETCD_ENABLE_V2=true
        volumes:
          - ./volumes/etcd:/etcd
        command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd

      minio:
        container_name: milvus-minio
        image: minio/minio:RELEASE.2022-09-17T00-09-45Z
        environment:
          MINIO_ACCESS_KEY: minioadmin
          MINIO_SECRET_KEY: minioadmin
        volumes:
          - ./volumes/minio:/minio_data
        command: minio server /minio_data
        healthcheck:
          test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
          interval: 30s
          timeout: 20s
          retries: 3

      standalone:
        container_name: milvus-standalone
        image: milvusdb/milvus:v2.3.3
        command: ["milvus", "run", "standalone"]
        environment:
          ETCD_ENDPOINTS: etcd:2379
          MINIO_ADDRESS: minio:9000
        volumes:
          - ./volumes/milvus:/var/lib/milvus
        ports:
          - "19530:19530"
          - "9091:9091"
        depends_on:
          - "etcd"
          - "minio"

    networks:
      default:
        name: milvus
    ```

3.  From your terminal, start the Milvus services:

    ```bash
    docker-compose up -d
    ```
    This command will start the `etcd`, `minio`, and `standalone` Milvus containers.

#### Step 3: Set Up the MySQL Database Manually

Since MySQL is not in the Docker setup, you must create the database for the application yourself.

1.  Make sure your local MySQL Server is running.
2.  Log in to MySQL as the root user.

    ```bash
    mysql -u root -p
    ```
    Enter your MySQL root password when prompted.

3.  Inside the MySQL shell, create the database that the application will use.

    ```sql
    CREATE DATABASE face_search_db;
    ```
4.  Exit the MySQL shell: `exit;`

**Important:** The Python code in `database.py` is configured to connect to MySQL with `username: root` and `password: Venu2425`. If your local MySQL root password is different, you **must** update the `DATABASE_URL` line in `database.py` accordingly.

#### Step 4: Set Up the Python Backend

1.  **Create a Virtual Environment:**

    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

2.  **Install Python Dependencies:**

    ```bash
    # Core dependencies
    pip install fastapi "uvicorn[standard]" sqlalchemy mysql-connector-python python-dotenv passlib geopy
    
    # AI model dependencies
    pip install numpy opencv-python onnx onnxruntime
    
    # Milvus and InsightFace
    pip install insightface pymilvus
    ```

#### Step 5: Create Project Directories

The application expects certain folders to exist for storing images.

```bash
# For macOS/Linux
mkdir images images_preview selected_images

# For Windows (using Command Prompt)
mkdir images
mkdir images_preview
mkdir selected_images
```
Docker will also automatically create a `./volumes` directory to store the Milvus data.

---

### 5. Running the Application

1.  Make sure your Milvus containers are running (`docker ps` should show them) and your local MySQL server is active.
2.  Ensure your Python virtual environment is activated.
3.  Run the FastAPI server using Uvicorn:

    ```bash
    uvicorn main_milvus:app --host 0.0.0.0 --port 8000 --reload
    ```

4.  The server is now live.

*   **Guest Portal:** `http://127.0.0.1:8000/`
*   **Admin Portal:** `http://127.0.0.1:8000/admin/login`

---

### 6. First-Time Admin Setup

On the first run, the system connects to your local MySQL, creates all the necessary tables, and adds a default admin account.

1.  Navigate to the admin login page: `http://127.0.0.1:8000/admin/login`.
2.  Log in with the default credentials:
    *   **Username:** `admin`
    *   **Password:** `admin123`
3.  We strongly recommend creating a new admin account with a secure password and then deleting the default `admin` user.

---

### 7. Project Folder Structure

```
.
├── admin_frontend/         # HTML, CSS, JS for the Admin Dashboard
├── frontend/               # HTML, CSS, JS for the Guest Portal
├── images/                 # Store your original high-res photo folders here
├── images_preview/         # Auto-generated by the app
├── selected_images/        # Auto-generated by the app
├── volumes/                # Auto-generated by Docker for Milvus, etcd, MinIO
│   ├── etcd/
│   ├── milvus/
│   └── minio/
├── venv/                   # Python virtual environment folder
├── database.py             # SQLAlchemy models and database setup
├── dependencies.py         # User authentication logic
├── Face_search_logic_milvus.py # Core AI and Milvus interaction logic
├── main_milvus.py          # Main FastAPI application
├── payment.py              # Payment simulation logic
└── docker-compose.yml      # Docker configuration for Milvus
