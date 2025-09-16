#!/usr/bin/env python3
"""
Script to reset and reinitialize the database with the correct schema
"""

import os
import sqlite3
from backend.src.database import init_db

def reset_database():
    """Remove existing database and create fresh one"""
    db_path = 'flood_data.db'
    
    # Remove existing database file if it exists
    if os.path.exists(db_path):
        print(f"Removing existing database: {db_path}")
        os.remove(db_path)
    
    # Initialize fresh database
    print("Creating fresh database with correct schema...")
    init_db(db_path)
    
    print("✅ Database reset complete!")
    
    # Verify the schema
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Check search_results table structure
    c.execute("PRAGMA table_info(search_results)")
    columns = c.fetchall()
    print("\n📋 search_results table structure:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Check all tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    print(f"\n📊 Database tables: {[table[0] for table in tables]}")
    
    conn.close()

if __name__ == "__main__":
    reset_database()