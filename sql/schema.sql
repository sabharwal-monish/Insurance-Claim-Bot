-- sql/schema.sql

CREATE DATABASE IF NOT EXISTS insurance_claims_db;

USE insurance_claims_db;

CREATE TABLE IF NOT EXISTS claims (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    policy_number VARCHAR(100),
    date_time_of_incident DATETIME,
    location_of_incident TEXT,
    type_of_incident VARCHAR(100),
    vehicle_info TEXT,
    description_of_incident TEXT,
    witness_info TEXT,
    police_report_details TEXT,
    photo_uploaded BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
