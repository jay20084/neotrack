# NeoTrack — Graph Database Courier Tracking Management System

A modern Courier Tracking and Logistics Management web application built with **FastAPI**, **Vis.js Graph Network**, and **Neo4j** (with an automatic zero-config **Mock Graph Engine** fallback).

---

## Features

- **Interactive 3D/2D Graph Explorer**: Visualizes entities (`Product`, `Customer`, `DeliveryPerson`, `CourierCompany`, `Address`, `TrackingEvent`) and relationships (`ORDERED`, `SHIPPED_BY`, `ASSIGNED_TO`, `ORIGINATED_AT`, `DESTINED_FOR`, `HAS_TRACKING_EVENT`).
- **Real-Time Shipment Insertion**: Modal to insert new shipments with custom package types (including Food/Perishables & Custom Requirement), dynamic agent assignment, and auto-generated IDs.
- **Delivery Status Updates**: Simulates dispatcher tracking updates (`Dispatched`, `Sorting`, `In Transit`, `Out for Delivery`, `Delivered`) and dynamically advances the visual transit stepper.
- **Smart Expected Delivery**: Displays `Today` when `0` days remain and turns into `Delivered` with vibrant green indicators when transit completes.
- **Zero-Config Fallback**: If Neo4j is not installed or running, the system automatically falls back to an in-memory **Mock Graph Engine** so anyone can run the application instantly without any database setup!

---

## Quick Start (For Reviewers)

### 1. Clone the Repository
```bash
git clone https://github.com/jay20084/neotrack.git
cd neotrack
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
uvicorn main:app --reload --port 8000
```

### 4. Open in Browser
Visit **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.

---

## (Optional) Running with Live Neo4j

If you want to connect to a live Neo4j database:
1. Start Neo4j Desktop or Docker (`bolt://localhost:7687`).
2. Copy `.env.example` to `.env` and configure your credentials:
   ```env
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=password
   ```
3. Restart the server. NeoTrack will automatically detect live Neo4j and use Cypher queries.

---

## Tech Stack
- **Backend**: Python 3.10+, FastAPI, Uvicorn, Pydantic, python-dotenv
- **Frontend**: HTML5, Tailwind CSS, Vis.js Network, Lucide Icons
- **Database**: Neo4j (Cypher) / In-Memory Mock Graph Engine
