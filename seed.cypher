// ============================================================================
// COURIER TRACKING MANAGEMENT SYSTEM - NEO4J CYPHER SEED SCRIPT
// Migrated from Legacy Oracle SQL & PL/SQL Database
// ============================================================================

// ----------------------------------------------------------------------------
// 1. UNIQUE CONSTRAINTS (Ensuring entity uniqueness and fast index lookups)
// ----------------------------------------------------------------------------
CREATE CONSTRAINT branch_id_unique IF NOT EXISTS FOR (b:Branch) REQUIRE b.branch_id IS UNIQUE;
CREATE CONSTRAINT company_id_unique IF NOT EXISTS FOR (c:CourierCompany) REQUIRE c.company_id IS UNIQUE;
CREATE CONSTRAINT customer_id_unique IF NOT EXISTS FOR (c:Customer) REQUIRE c.customer_id IS UNIQUE;
CREATE CONSTRAINT person_id_unique IF NOT EXISTS FOR (p:DeliveryPerson) REQUIRE p.person_id IS UNIQUE;
CREATE CONSTRAINT address_id_unique IF NOT EXISTS FOR (a:Address) REQUIRE a.address_id IS UNIQUE;
CREATE CONSTRAINT product_id_unique IF NOT EXISTS FOR (p:Product) REQUIRE p.product_id IS UNIQUE;
CREATE CONSTRAINT tracking_id_unique IF NOT EXISTS FOR (t:TrackingEvent) REQUIRE t.tracking_id IS UNIQUE;

// ----------------------------------------------------------------------------
// 2. NODES CREATION
// ----------------------------------------------------------------------------

// Branches (Logistics Hubs)
CREATE (b101:Branch {
    branch_id: 101,
    branch_name: 'Chennai Main Hub',
    branch_address: 'Guindy, Chennai'
});

CREATE (b102:Branch {
    branch_id: 102,
    branch_name: 'Bangalore Tech Hub',
    branch_address: 'Electronic City, Bangalore'
});

// Courier Companies
CREATE (c1:CourierCompany {
    company_id: 1,
    name: 'FastTrack Logistics',
    phone_no: '9876543210',
    email: 'contact@fasttrack.com'
});

CREATE (c2:CourierCompany {
    company_id: 2,
    name: 'Swift Parcel Co',
    phone_no: '9876543211',
    email: 'support@swiftparcel.com'
});

// Customers
CREATE (cust501:Customer {
    customer_id: 501,
    name: 'Adhithya V',
    phone_no: '9123456780'
});

CREATE (cust502:Customer {
    customer_id: 502,
    name: 'Vishnuvardhan G',
    phone_no: '9123456781'
});

CREATE (cust503:Customer {
    customer_id: 503,
    name: 'Jayesh R',
    phone_no: '9123456782'
});

// Delivery Agents
CREATE (dp201:DeliveryPerson {
    person_id: 201,
    name: 'Ramesh Kumar',
    phone_no: '9988776655'
});

CREATE (dp202:DeliveryPerson {
    person_id: 202,
    name: 'Suresh Reddy',
    phone_no: '9988776644'
});

// Addresses (Origin & Destination)
CREATE (addr301:Address {
    address_id: 301,
    house_no: '4A',
    street: 'Gandhi St',
    city: 'Chennai'
});

CREATE (addr302:Address {
    address_id: 302,
    house_no: '12B',
    street: 'MG Road',
    city: 'Bangalore'
});

CREATE (addr303:Address {
    address_id: 303,
    house_no: '10',
    street: 'Lake View',
    city: 'Coimbatore'
});

CREATE (addr304:Address {
    address_id: 304,
    house_no: '88',
    street: 'Park Ave',
    city: 'Chennai'
});

// Products / Parcels
CREATE (p1001:Product {
    product_id: 1001,
    product_name: 'Laptop',
    product_type: 'Electronics',
    product_size: 'Medium',
    weight: 2.50,
    status_id: 401,
    current_location: 'Bangalore Hub',
    expected_delivery: '+1 day'
});

CREATE (p1002:Product {
    product_id: 1002,
    product_name: 'Legal Documents',
    product_type: 'Paper',
    product_size: 'Small',
    weight: 0.20,
    status_id: 402,
    current_location: 'Chennai Sorting Center',
    expected_delivery: 'Today'
});

CREATE (p1003:Product {
    product_id: 1003,
    product_name: 'Gaming Monitor',
    product_type: 'Electronics',
    product_size: 'Large',
    weight: 6.80,
    status_id: 404,
    current_location: 'Delivered',
    expected_delivery: 'Delivered'
});

CREATE (p1004:Product {
    product_id: 1004,
    product_name: 'Wireless Mouse',
    product_type: 'Electronics',
    product_size: 'Small',
    weight: 0.15,
    status_id: 403,
    current_location: 'Chennai Dispatch Center',
    expected_delivery: '+2 days'
});

// Tracking Event Nodes (Time stamps in epoch milliseconds)
CREATE (t9001:TrackingEvent {
    tracking_id: 9001,
    arrival_time: timestamp() - (2 * 86400 * 1000),
    arrival_status: 'In Transit'
});

CREATE (t9002:TrackingEvent {
    tracking_id: 9002,
    arrival_time: timestamp() - (1 * 86400 * 1000),
    arrival_status: 'Arrived at Sorting Facility'
});

CREATE (t9003:TrackingEvent {
    tracking_id: 9003,
    arrival_time: timestamp() - (5 * 3600 * 1000),
    arrival_status: 'Out for Delivery'
});

CREATE (t9004:TrackingEvent {
    tracking_id: 9004,
    arrival_time: timestamp() - (3 * 86400 * 1000),
    arrival_status: 'Delivered'
});

CREATE (t9005:TrackingEvent {
    tracking_id: 9005,
    arrival_time: timestamp() - (2 * 3600 * 1000),
    arrival_status: 'Dispatched to Facility'
});

// ----------------------------------------------------------------------------
// 3. RELATIONSHIPS CREATION
// ----------------------------------------------------------------------------

// Company Locations at Branches
CREATE (c1)-[:LOCATED_AT]->(b101);
CREATE (c2)-[:LOCATED_AT]->(b102);

// Delivery Agents Employment
CREATE (dp201)-[:WORKS_FOR]->(c1);
CREATE (dp202)-[:WORKS_FOR]->(c2);

// Carrier Shipping
CREATE (p1001)-[:SHIPPED_BY]->(c1);
CREATE (p1002)-[:SHIPPED_BY]->(c2);
CREATE (p1003)-[:SHIPPED_BY]->(c1);
CREATE (p1004)-[:SHIPPED_BY]->(c2);

// Customer Orders
CREATE (cust501)-[:ORDERED]->(p1001);
CREATE (cust502)-[:ORDERED]->(p1002);
CREATE (cust501)-[:ORDERED]->(p1003);
CREATE (cust503)-[:ORDERED]->(p1004);

// Agent Assignments
CREATE (dp201)-[:ASSIGNED_TO]->(p1001);
CREATE (dp202)-[:ASSIGNED_TO]->(p1002);
CREATE (dp201)-[:ASSIGNED_TO]->(p1003);
CREATE (dp202)-[:ASSIGNED_TO]->(p1004);

// Transit Routing (Origin and Destination Addresses)
// Product 1001: Sender 301 (Gandhi St, Chennai) -> Receiver 302 (MG Road, Bangalore)
CREATE (p1001)-[:ORIGINATED_AT]->(addr301);
CREATE (p1001)-[:DESTINED_FOR]->(addr302);

// Product 1002: Sender 303 (Lake View, Coimbatore) -> Receiver 304 (Park Ave, Chennai)
CREATE (p1002)-[:ORIGINATED_AT]->(addr303);
CREATE (p1002)-[:DESTINED_FOR]->(addr304);

// Product 1003: Sender 301 (Gandhi St, Chennai) -> Receiver 303 (Lake View, Coimbatore)
CREATE (p1003)-[:ORIGINATED_AT]->(addr301);
CREATE (p1003)-[:DESTINED_FOR]->(addr303);

// Product 1004: Sender 304 (Park Ave, Chennai) -> Receiver 301 (Gandhi St, Chennai)
CREATE (p1004)-[:ORIGINATED_AT]->(addr304);
CREATE (p1004)-[:DESTINED_FOR]->(addr301);

// Tracking Event History Logs
CREATE (p1001)-[:HAS_TRACKING_EVENT]->(t9001);
CREATE (p1001)-[:HAS_TRACKING_EVENT]->(t9002);
CREATE (p1002)-[:HAS_TRACKING_EVENT]->(t9003);
CREATE (p1003)-[:HAS_TRACKING_EVENT]->(t9004);
CREATE (p1004)-[:HAS_TRACKING_EVENT]->(t9005);
