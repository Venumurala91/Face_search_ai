# Face Search AI - Docker Setup

## Prerequisites
- Docker
- Docker Compose

## How to Run
1.  Open a terminal in this directory.
2.  Run the following command to build and start the containers:
    ```bash
    docker-compose up -d --build
    ```

## Accessing the Application
- **Guest App**: [http://localhost:8000](http://localhost:8000)
- **Admin App**: [http://localhost:8000/admin/login](http://localhost:8000/admin/login)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

## Database Info
- **Type**: MySQL
- **Host**: localhost (externally mapped to port 3307) / `mysql` (internal docker hostname)
- **Port**: 3307 (external) / 3306 (internal)
- **User**: `root`
- **Password**: `root_password`
- **Database**: `face_search_db`

## Stopping the Application
To stop the containers, run:
```bash
docker-compose down
```
