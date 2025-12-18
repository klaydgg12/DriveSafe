# Database Configuration
# MySQL Database Settings

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # Change this to your MySQL username
    'password': 'mawan12',
    'database': 'drivesafe_db',
    'port': 3306
}

# You can also use environment variables for better security
# import os
# DB_CONFIG = {
#     'host': os.getenv('DB_HOST', 'localhost'),
#     'user': os.getenv('DB_USER', 'root'),
#     'password': os.getenv('DB_PASSWORD', ''),
#     'database': os.getenv('DB_NAME', 'drivesafe_db'),
#     'port': int(os.getenv('DB_PORT', 3306))
# }
