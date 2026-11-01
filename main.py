"""
Courier Tracking Management System (NeoTrack)
==============================================
Powered by Neo4j Graph Database, Python FastAPI, and Vis.js Graph Visualization.
Migrated from Legacy Oracle SQL & PL/SQL.
"""

import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Initialize Neo4j Driver (optional import fallback)
neo4j_driver = None
try:
    from neo4j import GraphDatabase, basic_auth
    try:
        # Create driver with quick connection timeout
        neo4j_driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD),
            connection_timeout=2.0
        )
    except Exception as e:
        print(f"[NeoTrack] Driver initialization warning: {e}")
        neo4j_driver = None
except ImportError:
    print("[NeoTrack] Warning: neo4j Python driver not installed.")

def sanitize_expected_delivery(val: Any) -> str:
    """Ensures 0/Today is 'Today', negative is 'Delivered', and positive is '+X days'."""
    if val is None:
        return "Today"
    s = str(val).strip()
    if not s:
        return "Today"
    if s.lower() == "today":
        return "Today"
    if s.lower() == "delivered":
        return "Delivered"
    if s.startswith("-"):
        return "Delivered"
    if s in ("0", "0 days", "0 day", "+0 days", "+0 day", "0d"):
        return "Today"
    try:
        clean = s.replace("days", "").replace("day", "").replace("+", "").strip()
        num = float(clean)
        if num < 0:
            return "Delivered"
        elif num == 0:
            return "Today"
    except ValueError:
        pass
    return s

# -----------------------------------------------------------------------------
# MOCK / FALLBACK GRAPH ENGINE
# Guarantees the dashboard works immediately even before Neo4j is launched
# -----------------------------------------------------------------------------
class MockGraphEngine:
    def __init__(self):
        self.clear()

    def clear(self):
        """Initial state: ZERO prerequisite records."""
        self.branches = {
            101: {"branch_id": 101, "branch_name": "Chennai Main Hub", "branch_address": "Guindy, Chennai"},
            102: {"branch_id": 102, "branch_name": "Bangalore Tech Hub", "branch_address": "Electronic City, Bangalore"},
        }
        self.companies = {
            1: {"company_id": 1, "name": "FastTrack Logistics", "phone_no": "9876543210", "email": "contact@fasttrack.com", "branch_id": 101},
            2: {"company_id": 2, "name": "Swift Parcel Co", "phone_no": "9876543211", "email": "support@swiftparcel.com", "branch_id": 102},
        }
        self.delivery_persons = {
            201: {"person_id": 201, "name": "Ramesh Kumar", "phone_no": "9988776655", "company_id": 1},
            202: {"person_id": 202, "name": "Suresh Reddy", "phone_no": "9988776644", "company_id": 2},
        }
        self.customers = {}
        self.addresses = {}
        self.products = {}
        self.tracking_events = {}
        self.next_tracking_id = 9001

    def reset_to_seed(self):
        """Seeds initial demo records if explicitly triggered."""
        self.clear()
        now_ms = int(time.time() * 1000)
        self.customers = {
            501: {"customer_id": 501, "name": "Adhithya V", "phone_no": "9123456780"},
            502: {"customer_id": 502, "name": "Vishnuvardhan G", "phone_no": "9123456781"},
            503: {"customer_id": 503, "name": "Jayesh R", "phone_no": "9123456782"},
        }
        self.addresses = {
            301: {"address_id": 301, "house_no": "4A", "street": "Gandhi St", "city": "Chennai"},
            302: {"address_id": 302, "house_no": "12B", "street": "MG Road", "city": "Bangalore"},
            303: {"address_id": 303, "house_no": "10", "street": "Lake View", "city": "Coimbatore"},
            304: {"address_id": 304, "house_no": "88", "street": "Park Ave", "city": "Chennai"},
        }
        self.products = {
            1001: {
                "product_id": 1001,
                "product_name": "Laptop",
                "product_type": "Electronics",
                "product_size": "Medium",
                "weight": 2.50,
                "status_id": 401,
                "current_location": "Bangalore Hub",
                "expected_delivery": "+1 day",
                "company_id": 1,
                "customer_id": 501,
                "delivery_person_id": 201,
                "origin_address_id": 301,
                "dest_address_id": 302,
                "tracking_ids": [9001, 9002]
            },
            1002: {
                "product_id": 1002,
                "product_name": "Legal Documents",
                "product_type": "Paper",
                "product_size": "Small",
                "weight": 0.20,
                "status_id": 402,
                "current_location": "Chennai Sorting Center",
                "expected_delivery": "Today",
                "company_id": 1,
                "customer_id": 502,
                "delivery_person_id": 202,
                "origin_address_id": 303,
                "dest_address_id": 304,
                "tracking_ids": [9003]
            },
            1003: {
                "product_id": 1003,
                "product_name": "Gaming Monitor",
                "product_type": "Electronics",
                "product_size": "Large",
                "weight": 6.80,
                "status_id": 404,
                "current_location": "Delivered",
                "expected_delivery": "Delivered",
                "company_id": 2,
                "customer_id": 501,
                "delivery_person_id": 202,
                "origin_address_id": 301,
                "dest_address_id": 303,
                "tracking_ids": [9004]
            },
            1004: {
                "product_id": 1004,
                "product_name": "Wireless Mouse",
                "product_type": "Electronics",
                "product_size": "Small",
                "weight": 0.15,
                "status_id": 403,
                "current_location": "Chennai Dispatch Center",
                "expected_delivery": "+2 days",
                "company_id": 2,
                "customer_id": 503,
                "delivery_person_id": 202,
                "origin_address_id": 304,
                "dest_address_id": 301,
                "tracking_ids": [9005]
            },
        }
        self.tracking_events = {
            9001: {"tracking_id": 9001, "arrival_time": now_ms - (2 * 86400 * 1000), "arrival_status": "In Transit"},
            9002: {"tracking_id": 9002, "arrival_time": now_ms - (1 * 86400 * 1000), "arrival_status": "Arrived at Sorting Facility"},
            9003: {"tracking_id": 9003, "arrival_time": now_ms - (5 * 3600 * 1000), "arrival_status": "Out for Delivery"},
            9004: {"tracking_id": 9004, "arrival_time": now_ms - (3 * 86400 * 1000), "arrival_status": "Delivered"},
            9005: {"tracking_id": 9005, "arrival_time": now_ms - (2 * 3600 * 1000), "arrival_status": "Dispatched to Facility"},
        }
        self.next_tracking_id = 9010

    def create_shipment(self, data: dict) -> int:
        pid = data.get("product_id")
        if not pid or pid in self.products:
            pid = max(self.products.keys()) + 1 if self.products else 1005

        cust_id = 500 + len(self.customers) + 1
        self.customers[cust_id] = {
            "customer_id": cust_id,
            "name": data["customer_name"],
            "phone_no": data.get("customer_phone", "9100000000"),
        }

        orig_id = 300 + (len(self.addresses) * 2) + 1
        self.addresses[orig_id] = {
            "address_id": orig_id,
            "house_no": data.get("origin_house_no", "1A"),
            "street": data.get("origin_street", "Gandhi St"),
            "city": data.get("origin_city", "Chennai"),
        }

        dest_id = orig_id + 1
        self.addresses[dest_id] = {
            "address_id": dest_id,
            "house_no": data.get("dest_house_no", "2B"),
            "street": data.get("dest_street", "MG Road"),
            "city": data.get("dest_city", "Bangalore"),
        }

        tid = self.next_tracking_id
        self.next_tracking_id += 1
        now_ms = int(time.time() * 1000)
        status_txt = data.get("initial_status", "Dispatched to Facility")
        self.tracking_events[tid] = {
            "tracking_id": tid,
            "arrival_time": now_ms,
            "arrival_status": status_txt
        }

        dp_name = (data.get("delivery_person_name") or "").strip()
        dp_id = data.get("delivery_person_id")

        if dp_name:
            matched_id = None
            for pid_existing, dp in self.delivery_persons.items():
                if dp.get("name", "").strip().lower() == dp_name.lower():
                    matched_id = pid_existing
                    break
            if matched_id:
                dp_id = matched_id
            else:
                dp_id = max(self.delivery_persons.keys(), default=200) + 1
                self.delivery_persons[dp_id] = {
                    "person_id": dp_id,
                    "name": dp_name,
                    "phone_no": f"998877{dp_id:04d}",
                    "company_id": int(data.get("company_id", 1))
                }
        else:
            if not dp_id:
                dp_id = 201
            if dp_id not in self.delivery_persons:
                self.delivery_persons[dp_id] = {
                    "person_id": dp_id,
                    "name": "Ramesh Kumar" if dp_id == 201 else f"Agent #{dp_id}",
                    "phone_no": "9988776655",
                    "company_id": int(data.get("company_id", 1))
                }

        status_id = 400 + len(self.products) + 1
        self.products[pid] = {
            "product_id": pid,
            "product_name": data["product_name"],
            "product_type": data.get("product_type", "Electronics"),
            "product_size": data.get("product_size", "Medium"),
            "weight": float(data.get("weight", 1.0)),
            "status_id": status_id,
            "current_location": data.get("current_location", "Origin Hub"),
            "expected_delivery": sanitize_expected_delivery(data.get("expected_delivery", "+2 days")),
            "company_id": int(data.get("company_id", 1)),
            "customer_id": cust_id,
            "delivery_person_id": dp_id,
            "origin_address_id": orig_id,
            "dest_address_id": dest_id,
            "tracking_ids": [tid],
        }
        return pid

mock_db = MockGraphEngine()

_last_neo4j_check = 0.0
_last_neo4j_alive = False

def is_neo4j_alive() -> bool:
    """Check if the live Neo4j database is accessible, cached for 5 seconds."""
    global neo4j_driver, _last_neo4j_check, _last_neo4j_alive
    now = time.time()
    if (now - _last_neo4j_check) < 5.0:
        return _last_neo4j_alive

    _last_neo4j_check = now
    if not neo4j_driver:
        try:
            from neo4j import GraphDatabase, basic_auth
            neo4j_driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD),
                connection_timeout=1.0
            )
        except Exception:
            _last_neo4j_alive = False
            return False

    try:
        neo4j_driver.verify_connectivity()
        _last_neo4j_alive = True
        return True
    except Exception:
        _last_neo4j_alive = False
        return False

# -----------------------------------------------------------------------------
# FASTAPI APP & TEMPLATES
# -----------------------------------------------------------------------------
app = FastAPI(
    title="NeoTrack - Courier Tracking Management System",
    description="Modern Graph Database Application replacing Oracle SQL & PL/SQL with Neo4j and Cypher",
    version="2.0.0"
)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# -----------------------------------------------------------------------------
# PYDANTIC SCHEMAS
# -----------------------------------------------------------------------------
class StatusUpdateIn(BaseModel):
    product_id: int
    new_location: str
    new_status: str
    days_to_add: int = 0

class CreateShipmentIn(BaseModel):
    product_id: Optional[int] = None
    product_name: str
    product_type: str = "Electronics"
    product_size: str = "Medium"
    weight: float = 1.50
    customer_name: str
    customer_phone: str = ""
    company_id: int = 1
    delivery_person_id: Optional[int] = None
    delivery_person_name: Optional[str] = None
    origin_city: str
    origin_street: str = "Gandhi St"
    origin_house_no: str = "10A"
    dest_city: str
    dest_street: str = "MG Road"
    dest_house_no: str = "24B"
    current_location: str = "Chennai Main Hub"
    expected_delivery: str = "+2 days"
    initial_status: str = "Dispatched to Facility"

# -----------------------------------------------------------------------------
# API ENDPOINTS
# -----------------------------------------------------------------------------

@app.get("/api/status/connection")
def get_connection_status():
    """Returns whether live Neo4j is connected or running in Mock Graph Engine mode."""
    live = is_neo4j_alive()
    return {
        "connected": live,
        "engine": "Neo4j Graph Database (Bolt)" if live else "Mock Graph Engine (In-Memory Fallback)",
        "uri": NEO4J_URI if live else "In-Memory Graph",
        "user": NEO4J_USER if live else "Local Simulation",
        "mode": "live" if live else "mock"
    }

@app.post("/api/seed")
def seed_database():
    """
    Clears and seeds the database with constraints, nodes, and relationships.
    Uses seed.cypher for live Neo4j, or resets MockGraphEngine if offline.
    """
    live = is_neo4j_alive()
    if live and neo4j_driver:
        cypher_file = BASE_DIR / "seed.cypher"
        if not cypher_file.exists():
            raise HTTPException(status_code=500, detail="seed.cypher file not found.")

        with open(cypher_file, "r", encoding="utf-8") as f:
            raw_script = f.read()

        # Split statements by semicolon while ignoring comments
        statements = []
        for stmt in raw_script.split(";"):
            clean_stmt = "\n".join(
                line for line in stmt.splitlines()
                if not line.strip().startswith("//")
            ).strip()
            if clean_stmt:
                statements.append(clean_stmt)

        try:
            with neo4j_driver.session() as session:
                # 1. Clean existing nodes and relationships
                session.run("MATCH (n) DETACH DELETE n")
                
                # 2. Run constraints and create statements
                for s in statements:
                    session.run(s)

            return {
                "status": "success",
                "engine": "Neo4j Live Database",
                "message": "Database wiped and re-seeded successfully with Cypher schema, constraints, nodes, and relationships!"
            }
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Neo4j seeding error: {str(err)}")
    else:
        mock_db.reset_to_seed()
        return {
            "status": "success",
            "engine": "Mock Graph Engine",
            "message": "In-memory Graph Engine seeded with initial dataset! (Neo4j server not detected; start Neo4j Desktop or Docker to switch to live DB)."
        }

@app.post("/api/reset")
@app.post("/api/clear")
def clear_database():
    """Completely resets/clears all records from the database to 0 records."""
    live = is_neo4j_alive()
    if live and neo4j_driver:
        try:
            with neo4j_driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
            return {"status": "success", "message": "Neo4j database wiped clean. 0 records."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        mock_db.clear()
        return {"status": "success", "message": "Database wiped clean. 0 records."}

@app.get("/api/shipments")
def get_shipments():
    """
    Replaces the 7-table SQL LEFT JOIN with Neo4j graph traversals.
    Returns all customers and their active shipment details.
    """
    live = is_neo4j_alive()
    if live and neo4j_driver:
        query = """
        MATCH (c:Customer)-[:ORDERED]->(p:Product)
        OPTIONAL MATCH (dp:DeliveryPerson)-[:ASSIGNED_TO]->(p)
        OPTIONAL MATCH (p)-[:ORIGINATED_AT]->(orig:Address)
        OPTIONAL MATCH (p)-[:DESTINED_FOR]->(dest:Address)
        OPTIONAL MATCH (p)-[:SHIPPED_BY]->(comp:CourierCompany)
        RETURN c.name AS customer_name,
               c.customer_id AS customer_id,
               c.phone_no AS customer_phone,
               p.product_id AS product_id,
               p.product_name AS product_name,
               p.product_type AS product_type,
               p.product_size AS product_size,
               p.weight AS weight,
               p.status_id AS status_id,
               dp.name AS delivery_person,
               dp.person_id AS delivery_person_id,
               comp.name AS company_name,
               p.current_location AS current_location,
               p.expected_delivery AS expected_delivery,
               orig.city AS sender_city,
               dest.city AS receiver_city,
               (orig.house_no + ', ' + orig.street + ', ' + orig.city) AS sender_address,
               (dest.house_no + ', ' + dest.street + ', ' + dest.city) AS receiver_address
        ORDER BY p.product_id ASC
        """
        try:
            with neo4j_driver.session() as session:
                result = session.run(query)
                records = []
                for r in result:
                    records.append({
                        "customer_name": r["customer_name"],
                        "customer_id": r["customer_id"],
                        "customer_phone": r["customer_phone"],
                        "product_id": r["product_id"],
                        "product_name": r["product_name"],
                        "product_type": r["product_type"],
                        "product_size": r["product_size"],
                        "weight": float(r["weight"]) if r["weight"] is not None else 0.0,
                        "status_id": r["status_id"],
                        "delivery_person": r["delivery_person"] or "Unassigned",
                        "delivery_person_id": r.get("delivery_person_id"),
                        "company_name": r["company_name"] or "Independent",
                        "current_location": r["current_location"],
                        "expected_delivery": sanitize_expected_delivery(r["expected_delivery"]),
                        "sender_city": r["sender_city"] or "Unknown",
                        "receiver_city": r["receiver_city"] or "Unknown",
                        "sender_address": r["sender_address"] or "N/A",
                        "receiver_address": r["receiver_address"] or "N/A",
                    })
                return records
        except Exception as e:
            print(f"[NeoTrack] Fallback query error: {e}")

    # Fallback to Mock Graph Engine
    records = []
    for pid, p in sorted(mock_db.products.items()):
        cust = mock_db.customers.get(p.get("customer_id"), {})
        dp = mock_db.delivery_persons.get(p.get("delivery_person_id"), {})
        comp = mock_db.companies.get(p.get("company_id"), {})
        orig = mock_db.addresses.get(p.get("origin_address_id"), {})
        dest = mock_db.addresses.get(p.get("dest_address_id"), {})

        sender_addr = f"{orig.get('house_no', '')}, {orig.get('street', '')}, {orig.get('city', '')}".strip(", ")
        receiver_addr = f"{dest.get('house_no', '')}, {dest.get('street', '')}, {dest.get('city', '')}".strip(", ")

        records.append({
            "customer_name": cust.get("name", "Unknown"),
            "customer_id": cust.get("customer_id", 0),
            "customer_phone": cust.get("phone_no", ""),
            "product_id": p["product_id"],
            "product_name": p["product_name"],
            "product_type": p["product_type"],
            "product_size": p["product_size"],
            "weight": p["weight"],
            "status_id": p["status_id"],
            "delivery_person": dp.get("name", "Unassigned"),
            "delivery_person_id": p.get("delivery_person_id"),
            "company_name": comp.get("name", "N/A"),
            "current_location": p["current_location"],
            "expected_delivery": sanitize_expected_delivery(p["expected_delivery"]),
            "sender_city": orig.get("city", "Unknown"),
            "receiver_city": dest.get("city", "Unknown"),
            "sender_address": sender_addr,
            "receiver_address": receiver_addr,
        })
    return records

@app.get("/api/track/{product_id}")
def track_product(product_id: int):
    """
    Returns full details for a single product, its chronologically ordered
    TrackingEvent logs (replaces the PL/SQL cursor loop), and graph_data for Vis.js.
    """
    live = is_neo4j_alive()
    if live and neo4j_driver:
        query_prod = """
        MATCH (p:Product {product_id: $pid})
        OPTIONAL MATCH (c:Customer)-[:ORDERED]->(p)
        OPTIONAL MATCH (dp:DeliveryPerson)-[:ASSIGNED_TO]->(p)
        OPTIONAL MATCH (p)-[:SHIPPED_BY]->(comp:CourierCompany)-[:LOCATED_AT]->(b:Branch)
        OPTIONAL MATCH (p)-[:ORIGINATED_AT]->(orig:Address)
        OPTIONAL MATCH (p)-[:DESTINED_FOR]->(dest:Address)
        RETURN p, c, dp, comp, b, orig, dest
        """
        query_events = """
        MATCH (p:Product {product_id: $pid})-[:HAS_TRACKING_EVENT]->(t:TrackingEvent)
        RETURN t.tracking_id AS tracking_id,
               t.arrival_time AS arrival_time,
               t.arrival_status AS arrival_status
        ORDER BY t.arrival_time ASC
        """
        try:
            with neo4j_driver.session() as session:
                res_prod = session.run(query_prod, pid=product_id).single()
                if not res_prod:
                    raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found.")

                p_node = dict(res_prod["p"])
                p_node["expected_delivery"] = sanitize_expected_delivery(p_node.get("expected_delivery"))
                c_node = dict(res_prod["c"]) if res_prod["c"] else None
                dp_node = dict(res_prod["dp"]) if res_prod["dp"] else None
                comp_node = dict(res_prod["comp"]) if res_prod["comp"] else None
                b_node = dict(res_prod["b"]) if res_prod["b"] else None
                orig_node = dict(res_prod["orig"]) if res_prod["orig"] else None
                dest_node = dict(res_prod["dest"]) if res_prod["dest"] else None

                res_events = session.run(query_events, pid=product_id)
                events = []
                for ev in res_events:
                    raw_time = ev["arrival_time"]
                    if isinstance(raw_time, (int, float)):
                        ts_str = datetime.fromtimestamp(raw_time / 1000.0).strftime("%Y-%m-%d %H:%M")
                    else:
                        ts_str = str(raw_time)
                    events.append({
                        "tracking_id": ev["tracking_id"],
                        "arrival_time": ts_str,
                        "arrival_status": ev["arrival_status"]
                    })

                # Build Vis.js graph nodes and edges
                graph_data = build_vis_graph(
                    product=p_node,
                    customer=c_node,
                    delivery_person=dp_node,
                    company=comp_node,
                    branch=b_node,
                    origin=orig_node,
                    dest=dest_node,
                    events=events
                )

                return {
                    "product": p_node,
                    "customer": c_node,
                    "delivery_person": dp_node,
                    "company": comp_node,
                    "branch": b_node,
                    "origin": orig_node,
                    "dest": dest_node,
                    "tracking_events": events,
                    "graph_data": graph_data
                }
        except HTTPException:
            raise
        except Exception as err:
            print(f"[NeoTrack] Graph fetch error: {err}")

    # Fallback to Mock Engine
    if product_id not in mock_db.products:
        raise HTTPException(status_code=404, detail=f"Product ID {product_id} not found.")

    p = mock_db.products[product_id]
    p["expected_delivery"] = sanitize_expected_delivery(p.get("expected_delivery"))
    c = mock_db.customers.get(p.get("customer_id"))
    dp = mock_db.delivery_persons.get(p.get("delivery_person_id"))
    comp = mock_db.companies.get(p.get("company_id"))
    b = mock_db.branches.get(comp.get("branch_id")) if comp else None
    orig = mock_db.addresses.get(p.get("origin_address_id"))
    dest = mock_db.addresses.get(p.get("dest_address_id"))

    events = []
    for tid in p.get("tracking_ids", []):
        if tid in mock_db.tracking_events:
            ev = mock_db.tracking_events[tid]
            raw_time = ev["arrival_time"]
            ts_str = datetime.fromtimestamp(raw_time / 1000.0).strftime("%Y-%m-%d %H:%M")
            events.append({
                "tracking_id": ev["tracking_id"],
                "arrival_time": ts_str,
                "arrival_status": ev["arrival_status"]
            })
    events.sort(key=lambda x: x["tracking_id"])

    graph_data = build_vis_graph(p, c, dp, comp, b, orig, dest, events)
    return {
        "product": p,
        "customer": c,
        "delivery_person": dp,
        "company": comp,
        "branch": b,
        "origin": orig,
        "dest": dest,
        "tracking_events": events,
        "graph_data": graph_data
    }

def build_vis_graph(product, customer, delivery_person, company, branch, origin, dest, events):
    """Formats graph nodes and relationships for Vis.js Network rendering."""
    nodes = []
    edges = []
    added_nodes = set()

    def add_n(nid: str, label: str, group: str, title: str, color_bg: str, color_border: str):
        if nid not in added_nodes:
            nodes.append({
                "id": nid,
                "label": label,
                "group": group,
                "title": title,
                "color": {
                    "background": color_bg,
                    "border": color_border,
                    "highlight": {"background": color_bg, "border": "#FFFFFF"}
                },
                "font": {"color": "#FFFFFF", "size": 13, "bold": True},
                "shadow": True
            })
            added_nodes.add(nid)

    def add_e(from_id: str, to_id: str, label: str, color: str = "#94A3B8"):
        edges.append({
            "from": from_id,
            "to": to_id,
            "label": label,
            "arrows": "to",
            "color": {"color": color, "highlight": "#38BDF8"},
            "font": {"size": 10, "align": "middle", "color": "#CBD5E1"},
            "smooth": {"type": "curvedCW", "roundness": 0.15}
        })

    pid = product["product_id"]
    p_node_id = f"prod_{pid}"
    add_n(
        p_node_id,
        f"📦 {product['product_name']}\n(#{pid})",
        "Product",
        f"Product: {product['product_name']} | Weight: {product.get('weight')}kg | Status: {product.get('current_location')}",
        "#6366F1", "#4F46E5"
    )

    if customer:
        cid = customer["customer_id"]
        c_node_id = f"cust_{cid}"
        add_n(
            c_node_id,
            f"👤 {customer['name']}\n(#{cid})",
            "Customer",
            f"Customer: {customer['name']} | Phone: {customer.get('phone_no')}",
            "#3B82F6", "#2563EB"
        )
        add_e(c_node_id, p_node_id, "ORDERED", "#60A5FA")

    if delivery_person:
        dpid = delivery_person["person_id"]
        dp_node_id = f"dp_{dpid}"
        add_n(
            dp_node_id,
            f"🚚 {delivery_person['name']}\n(Agent #{dpid})",
            "DeliveryPerson",
            f"Courier Agent: {delivery_person['name']} | Phone: {delivery_person.get('phone_no')}",
            "#F59E0B", "#D97706"
        )
        add_e(dp_node_id, p_node_id, "ASSIGNED_TO", "#FBBF24")

    if company:
        comp_id = company["company_id"]
        comp_node_id = f"comp_{comp_id}"
        add_n(
            comp_node_id,
            f"🏢 {company['name']}",
            "CourierCompany",
            f"Company: {company['name']} | Email: {company.get('email')}",
            "#A855F7", "#9333EA"
        )
        add_e(p_node_id, comp_node_id, "SHIPPED_BY", "#C084FC")

        if branch:
            bid = branch["branch_id"]
            b_node_id = f"branch_{bid}"
            add_n(
                b_node_id,
                f"🏛️ {branch['branch_name']}",
                "Branch",
                f"Hub: {branch['branch_name']} | Address: {branch.get('branch_address')}",
                "#14B8A6", "#0D9488"
            )
            add_e(comp_node_id, b_node_id, "LOCATED_AT", "#2DD4BF")

    if origin:
        orig_id = origin["address_id"]
        orig_node_id = f"addr_{orig_id}_orig"
        add_n(
            orig_node_id,
            f"📍 Origin\n{origin.get('city', '')}",
            "Address",
            f"From: {origin.get('house_no')}, {origin.get('street')}, {origin.get('city')}",
            "#10B981", "#059669"
        )
        add_e(p_node_id, orig_node_id, "ORIGINATED_AT", "#34D399")

    if dest:
        dest_id = dest["address_id"]
        dest_node_id = f"addr_{dest_id}_dest"
        add_n(
            dest_node_id,
            f"🎯 Destination\n{dest.get('city', '')}",
            "Address",
            f"To: {dest.get('house_no')}, {dest.get('street')}, {dest.get('city')}",
            "#059669", "#047857"
        )
        add_e(p_node_id, dest_node_id, "DESTINED_FOR", "#10B981")

    for ev in events:
        tid = ev["tracking_id"]
        t_node_id = f"track_{tid}"
        add_n(
            t_node_id,
            f"⏱️ {ev['arrival_status']}\n{ev['arrival_time']}",
            "TrackingEvent",
            f"Event #{tid}: {ev['arrival_status']} at {ev['arrival_time']}",
            "#F43F5E", "#E11D48"
        )
        add_e(p_node_id, t_node_id, "HAS_TRACKING_EVENT", "#FB7185")

    return {"nodes": nodes, "edges": edges}

@app.post("/api/status/update")
def update_delivery_status(payload: StatusUpdateIn):
    """
    Replaces the PL/SQL stored procedure update_delivery_status(p_status_id, p_new_location, p_days_to_add).
    Updates current_location and expected_delivery, adds a TrackingEvent node with current timestamp.
    """
    pid = payload.product_id
    new_loc = payload.new_location.strip()
    new_stat = payload.new_status.strip()

    # Calculate new expected delivery (0 = Today, < 0 or delivered = Delivered, > 0 = +X days)
    if new_stat.lower() == "delivered" or payload.days_to_add < 0:
        new_expected = "Delivered"
    elif payload.days_to_add == 0:
        new_expected = "Today"
    elif payload.days_to_add == 1:
        new_expected = "+1 day"
    else:
        new_expected = f"+{payload.days_to_add} days"

    live = is_neo4j_alive()
    if live and neo4j_driver:
        # Check product existence
        check_q = "MATCH (p:Product {product_id: $pid}) RETURN p"
        update_q = """
        MATCH (p:Product {product_id: $pid})
        SET p.current_location = $loc,
            p.expected_delivery = $expected
        WITH p
        CREATE (t:TrackingEvent {
            tracking_id: toInteger(timestamp() / 1000),
            arrival_time: timestamp(),
            arrival_status: $status
        })
        CREATE (p)-[:HAS_TRACKING_EVENT]->(t)
        RETURN p.product_id AS product_id, t.tracking_id AS tracking_id
        """
        try:
            with neo4j_driver.session() as session:
                res = session.run(check_q, pid=pid).single()
                if not res:
                    raise HTTPException(status_code=404, detail=f"Product #{pid} does not exist in Neo4j.")

                session.run(update_q, pid=pid, loc=new_loc, expected=new_expected, status=new_stat)
                return {
                    "status": "success",
                    "product_id": pid,
                    "new_location": new_loc,
                    "new_status": new_stat,
                    "expected_delivery": new_expected,
                    "message": f"Successfully updated Product #{pid} in Neo4j! New tracking event added."
                }
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Database update failed: {str(err)}")

    # Fallback to Mock Engine
    if pid not in mock_db.products:
        raise HTTPException(status_code=404, detail=f"Product #{pid} not found in shipment records.")

    p = mock_db.products[pid]
    p["current_location"] = new_loc
    p["expected_delivery"] = new_expected

    # Create new tracking event
    new_tid = mock_db.next_tracking_id
    mock_db.next_tracking_id += 1
    mock_db.tracking_events[new_tid] = {
        "tracking_id": new_tid,
        "arrival_time": int(time.time() * 1000),
        "arrival_status": new_stat
    }
    p["tracking_ids"].append(new_tid)

    return {
        "status": "success",
        "product_id": pid,
        "new_location": new_loc,
        "new_status": new_stat,
        "expected_delivery": new_expected,
        "message": f"Successfully updated Product #{pid} (Mock Engine)! Timeline and graph synchronized."
    }

@app.post("/api/shipment/create")
def create_shipment_endpoint(payload: CreateShipmentIn):
    """
    Inserts a new shipment record with Customer, Origin/Dest Addresses,
    Courier Company, Delivery Person, and initial Tracking Event into the Graph Database.
    """
    live = is_neo4j_alive()
    if live and neo4j_driver:
        pid = payload.product_id
        if not pid:
            find_max_q = "MATCH (p:Product) RETURN coalesce(max(p.product_id), 1004) + 1 AS next_pid"
            try:
                with neo4j_driver.session() as session:
                    max_res = session.run(find_max_q).single()
                    pid = max_res["next_pid"] if (max_res and max_res["next_pid"]) else int(time.time() % 100000)
            except Exception:
                pid = 1005

        ts_now = int(time.time() * 1000)
        cust_id = int(ts_now % 9000) + 1000
        orig_id = int((ts_now + 1) % 9000) + 1000
        dest_id = int((ts_now + 2) % 9000) + 1000
        track_id = int(ts_now / 1000)
        status_id = int(ts_now % 500) + 410

        dp_name = (payload.delivery_person_name or "").strip()
        dp_id = payload.delivery_person_id

        if dp_name:
            find_dp_q = "MATCH (dp:DeliveryPerson) WHERE toLower(dp.name) = toLower($name) RETURN dp.person_id AS pid, dp.name AS name LIMIT 1"
            try:
                with neo4j_driver.session() as session:
                    found = session.run(find_dp_q, name=dp_name).single()
                    if found:
                        dp_id = found["pid"]
                        dp_name = found["name"]
                    elif not dp_id:
                        max_dp_q = "MATCH (dp:DeliveryPerson) RETURN coalesce(max(dp.person_id), 200) + 1 AS next_dp_id"
                        max_res = session.run(max_dp_q).single()
                        dp_id = max_res["next_dp_id"] if max_res else 201
            except Exception:
                if not dp_id:
                    dp_id = 201
        else:
            if not dp_id:
                dp_id = 201
            dp_name = "Ramesh Kumar" if dp_id == 201 else f"Agent #{dp_id}"

        cypher_create = """
        MERGE (c:CourierCompany {company_id: $company_id})
        ON CREATE SET c.name = CASE $company_id WHEN 1 THEN 'FastTrack Logistics' WHEN 2 THEN 'Swift Parcel Co' ELSE 'Courier #' + toString($company_id) END
        ON MATCH SET c.name = CASE WHEN c.name IS NULL OR c.name = '' THEN (CASE $company_id WHEN 1 THEN 'FastTrack Logistics' WHEN 2 THEN 'Swift Parcel Co' ELSE 'Courier #' + toString($company_id) END) ELSE c.name END
        MERGE (dp:DeliveryPerson {person_id: $dp_id})
        ON CREATE SET dp.name = $dp_name, dp.phone_no = '9988776655'
        ON MATCH SET dp.name = CASE WHEN dp.name IS NULL OR dp.name = '' THEN $dp_name ELSE dp.name END
        
        CREATE (cust:Customer {
            customer_id: $cust_id,
            name: $cust_name,
            phone_no: $cust_phone
        })
        
        CREATE (orig:Address {
            address_id: $orig_id,
            house_no: $orig_house,
            street: $orig_street,
            city: $orig_city
        })
        
        CREATE (dest:Address {
            address_id: $dest_id,
            house_no: $dest_house,
            street: $dest_street,
            city: $dest_city
        })
        
        CREATE (p:Product {
            product_id: $pid,
            product_name: $pname,
            product_type: $ptype,
            product_size: $psize,
            weight: $weight,
            status_id: $status_id,
            current_location: $curr_loc,
            expected_delivery: $expected
        })
        
        CREATE (t:TrackingEvent {
            tracking_id: $track_id,
            arrival_time: timestamp(),
            arrival_status: $status
        })
        
        CREATE (cust)-[:ORDERED]->(p)
        CREATE (p)-[:SHIPPED_BY]->(c)
        CREATE (dp)-[:ASSIGNED_TO]->(p)
        CREATE (p)-[:ORIGINATED_AT]->(orig)
        CREATE (p)-[:DESTINED_FOR]->(dest)
        CREATE (p)-[:HAS_TRACKING_EVENT]->(t)
        RETURN p.product_id AS product_id
        """
        try:
            with neo4j_driver.session() as session:
                session.run(
                    cypher_create,
                    company_id=payload.company_id,
                    dp_id=dp_id,
                    dp_name=dp_name,
                    cust_id=cust_id,
                    cust_name=payload.customer_name,
                    cust_phone=payload.customer_phone or "9123456799",
                    orig_id=orig_id,
                    orig_house=payload.origin_house_no,
                    orig_street=payload.origin_street,
                    orig_city=payload.origin_city,
                    dest_id=dest_id,
                    dest_house=payload.dest_house_no,
                    dest_street=payload.dest_street,
                    dest_city=payload.dest_city,
                    pid=pid,
                    pname=payload.product_name,
                    ptype=payload.product_type,
                    psize=payload.product_size,
                    weight=payload.weight,
                    status_id=status_id,
                    curr_loc=payload.current_location,
                    expected=sanitize_expected_delivery(payload.expected_delivery),
                    track_id=track_id,
                    status=payload.initial_status
                )
                return {
                    "status": "success",
                    "product_id": pid,
                    "message": f"Successfully inserted Shipment #{pid} ({payload.product_name}) and graph relationships into Neo4j!"
                }
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Neo4j insertion failed: {str(err)}")

    # Fallback to Mock Engine
    data_dict = payload.model_dump()
    new_pid = mock_db.create_shipment(data_dict)
    return {
        "status": "success",
        "product_id": new_pid,
        "message": f"Successfully inserted Shipment #{new_pid} ({payload.product_name}) into Mock Graph Engine!"
    }

@app.get("/api/analytics")
def get_analytics():
    """
    Replaces the SQL GROUP BY ... HAVING AVG(weight) > 0.5 query
    and the get_avg_product_weight(company_id) PL/SQL function.
    Returns average product weight per company, overall average weight, and counts.
    """
    live = is_neo4j_alive()
    if live and neo4j_driver:
        company_query = """
        MATCH (c:CourierCompany)<-[:SHIPPED_BY]-(p:Product)
        RETURN c.company_id AS company_id,
               coalesce(c.name, CASE c.company_id WHEN 1 THEN 'FastTrack Logistics' WHEN 2 THEN 'Swift Parcel Co' ELSE 'Company #' + toString(c.company_id) END) AS company_name,
               round(avg(p.weight) * 100) / 100.0 AS avg_weight,
               count(p) AS package_count
        ORDER BY c.company_id
        """
        category_query = """
        MATCH (p:Product)
        RETURN p.product_type AS category,
               count(p) AS count,
               round(avg(p.weight) * 100) / 100.0 AS avg_weight
        ORDER BY avg_weight DESC
        """
        overall_query = """
        MATCH (p:Product)
        RETURN count(p) AS total_count,
               coalesce(round(avg(p.weight) * 100) / 100.0, 0.0) AS overall_avg_weight
        """
        try:
            with neo4j_driver.session() as session:
                comp_rows = session.run(company_query).data()
                cat_rows = session.run(category_query).data()
                ov_res = session.run(overall_query).single()

                total_shipments = ov_res["total_count"] if ov_res else 0
                overall_avg = float(ov_res["overall_avg_weight"]) if ov_res else 0.0

                comp_map = {
                    1: {"company_id": 1, "company_name": "FastTrack Logistics", "avg_weight": 0.0, "package_count": 0},
                    2: {"company_id": 2, "company_name": "Swift Parcel Co", "avg_weight": 0.0, "package_count": 0},
                }
                for r in comp_rows:
                    cid = r["company_id"]
                    comp_map[cid] = {
                        "company_id": cid,
                        "company_name": r.get("company_name") or ("FastTrack Logistics" if cid == 1 else "Swift Parcel Co"),
                        "avg_weight": float(r["avg_weight"] or 0.0),
                        "package_count": int(r["package_count"] or 0)
                    }

                heavy_categories = [cat for cat in cat_rows if cat["avg_weight"] > 0.5]

                return {
                    "total_active_shipments": total_shipments,
                    "overall_avg_weight": overall_avg,
                    "companies": list(comp_map.values()),
                    "categories": cat_rows,
                    "heavy_category_alert": heavy_categories[0] if heavy_categories else None,
                    "engine": "Neo4j Cypher Analytics"
                }
        except Exception as e:
            print(f"[NeoTrack] Analytics query error: {e}")

    # Fallback to Mock Engine
    total_active = len(mock_db.products)
    all_weights = [float(p["weight"]) for p in mock_db.products.values() if p.get("weight") is not None]
    overall_avg = round(sum(all_weights) / len(all_weights), 2) if all_weights else 0.0

    comp_defaults = {
        1: {"company_id": 1, "company_name": "FastTrack Logistics", "weights": []},
        2: {"company_id": 2, "company_name": "Swift Parcel Co", "weights": []},
    }
    for p in mock_db.products.values():
        cid = p.get("company_id", 1)
        if cid not in comp_defaults:
            comp_name = mock_db.companies.get(cid, {}).get("name", f"Courier #{cid}")
            comp_defaults[cid] = {"company_id": cid, "company_name": comp_name, "weights": []}
        comp_defaults[cid]["weights"].append(float(p.get("weight", 0.0)))

    companies = []
    for cid, data in sorted(comp_defaults.items()):
        w_list = data["weights"]
        avg_w = round(sum(w_list) / len(w_list), 2) if w_list else 0.0
        companies.append({
            "company_id": cid,
            "company_name": data["company_name"],
            "avg_weight": avg_w,
            "package_count": len(w_list)
        })

    cat_stats = {}
    for p in mock_db.products.values():
        cat = p.get("product_type", "General")
        if cat not in cat_stats:
            cat_stats[cat] = {"category": cat, "weights": []}
        cat_stats[cat]["weights"].append(float(p.get("weight", 0.0)))

    categories = []
    for cat, data in cat_stats.items():
        w_list = data["weights"]
        avg_w = round(sum(w_list) / len(w_list), 2) if w_list else 0.0
        categories.append({
            "category": cat,
            "count": len(w_list),
            "avg_weight": avg_w
        })
    categories.sort(key=lambda x: x["avg_weight"], reverse=True)

    heavy_categories = [c for c in categories if c["avg_weight"] > 0.5]

    return {
        "total_active_shipments": total_active,
        "overall_avg_weight": overall_avg,
        "companies": companies,
        "categories": categories,
        "heavy_category_alert": heavy_categories[0] if heavy_categories else None,
        "engine": "Mock Graph Engine Analytics"
    }

@app.get("/api/hub-products/{branch_name}")
def get_hub_products(branch_name: str):
    """
    Replaces the SQL INNER JOIN subquery (WHERE branch_name = 'Chennai Main Hub').
    Lists all products shipped by courier companies located at the given hub.
    """
    live = is_neo4j_alive()
    if live and neo4j_driver:
        query = """
        MATCH (b:Branch {branch_name: $bname})<-[:LOCATED_AT]-(c:CourierCompany)<-[:SHIPPED_BY]-(p:Product)
        OPTIONAL MATCH (cust:Customer)-[:ORDERED]->(p)
        OPTIONAL MATCH (dp:DeliveryPerson)-[:ASSIGNED_TO]->(p)
        OPTIONAL MATCH (p)-[:ORIGINATED_AT]->(orig:Address)
        OPTIONAL MATCH (p)-[:DESTINED_FOR]->(dest:Address)
        RETURN p.product_id AS product_id,
               p.product_name AS product_name,
               p.product_type AS product_type,
               p.weight AS weight,
               c.name AS company_name,
               b.branch_name AS branch_name,
               cust.name AS customer_name,
               dp.name AS delivery_person,
               p.current_location AS location,
               p.expected_delivery AS expected_delivery,
               orig.city AS sender_city,
               dest.city AS receiver_city
        ORDER BY p.product_id ASC
        """
        try:
            with neo4j_driver.session() as session:
                rows = session.run(query, bname=branch_name).data()
                return rows
        except Exception as err:
            print(f"[NeoTrack] Hub products error: {err}")

    # Fallback to Mock Engine
    # Find branch ID
    target_bid = None
    for bid, b in mock_db.branches.items():
        if b["branch_name"].lower() == branch_name.lower():
            target_bid = bid
            break

    if not target_bid:
        return []

    comp_ids = [cid for cid, c in mock_db.companies.items() if c.get("branch_id") == target_bid]
    results = []
    for p in mock_db.products.values():
        if p.get("company_id") in comp_ids:
            cust = mock_db.customers.get(p.get("customer_id"), {})
            dp = mock_db.delivery_persons.get(p.get("delivery_person_id"), {})
            comp = mock_db.companies.get(p.get("company_id"), {})
            b = mock_db.branches.get(target_bid, {})
            orig = mock_db.addresses.get(p.get("origin_address_id"), {})
            dest = mock_db.addresses.get(p.get("dest_address_id"), {})
            results.append({
                "product_id": p["product_id"],
                "product_name": p["product_name"],
                "product_type": p["product_type"],
                "weight": p["weight"],
                "company_name": comp.get("name", "N/A"),
                "branch_name": b.get("branch_name", branch_name),
                "customer_name": cust.get("name", "Unknown"),
                "delivery_person": dp.get("name", "Unassigned"),
                "location": p["current_location"],
                "expected_delivery": p["expected_delivery"],
                "sender_city": orig.get("city", "Unknown"),
                "receiver_city": dest.get("city", "Unknown"),
            })
    return results

# -----------------------------------------------------------------------------
# FRONTEND ROOT ROUTE
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request = None):
    root_index = BASE_DIR / "index.html"
    if root_index.exists():
        return HTMLResponse(content=root_index.read_text(encoding="utf-8"))
    templates_index = BASE_DIR / "templates" / "index.html"
    if templates_index.exists():
        return HTMLResponse(content=templates_index.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="index.html not found.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
