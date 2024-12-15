"""
This module defines PostgreSQL database connection parameters:  
- Reads the password securely from the `PGPASSWORD` environment variable.  
- Provides a configuration dictionary (`PGSQL_CONFIG_DICT`) with placeholders for user, host, port, password, database, and table.  

IMPORTANT: Users must customize the values in `PGSQL_CONFIG_DICT` to match their specific database configuration.
"""

import os

PGPASSWORD = os.environ.get('PGPASSWORD') 

PGSQL_CONFIG_DICT = {
    "user": "postgres",                    
    "host": "172.17.0.1",                
    "port": "5432",                       
    "password": PGPASSWORD,              
    "database": "parking_lyon_db",       
    "table": "parking_table"          
}