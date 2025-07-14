import json
import os
import psycopg2
import logging
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(
            host=os.environ['PG_HOST'],
            port=os.environ['PG_PORT'],
            database=os.environ['PG_DB'],
            user=os.environ['PG_USER'],
            password=os.environ['PG_PASSWORD']
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise

def authenticate_user(conn, username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user against database"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT username, password_hash, home_directory, is_active
            FROM ftp_users 
            WHERE username = %s AND is_active = TRUE
        """, (username,))
        
        result = cursor.fetchone()
        cursor.close()
        
        if not result:
            logger.warning(f"User not found or inactive: {username}")
            return None
        
        db_username, password_hash, home_directory, is_active = result
        
        # Simple password check (in production, use proper password hashing)
        if password != password_hash:
            logger.warning(f"Invalid password for user: {username}")
            return None
        
        return {
            'username': db_username,
            'home_directory': home_directory,
            'role_arn': 'arn:aws:iam::aws:policy/AWSTransferConsoleFullAccess',
            'is_active': is_active
        }
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        return None

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Transfer Family custom authentication
    
    Expected event format:
    {
        "username": "user123",
        "password": "password123",
        "protocol": "SFTP",
        "serverId": "s-1234567890abcdef0",
        "sourceIp": "192.168.1.1"
    }
    """
    try:
        logger.info(f"Received authentication request: {json.dumps(event)}")
        
        # Extract authentication details
        username = event.get('username')
        password = event.get('password')
        protocol = event.get('protocol', 'SFTP')
        server_id = event.get('serverId')
        source_ip = event.get('sourceIp')
        
        if not username or not password:
            logger.error("Missing username or password")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing username or password'
                })
            }
        
        # Connect to database
        conn = get_db_connection()
        
        
        # Authenticate user
        user_data = authenticate_user(conn, username, password)
        
        if not user_data:
            logger.warning(f"Authentication failed for user: {username}")
            return {
                'statusCode': 401,
                'body': json.dumps({
                    'error': 'Authentication failed'
                })
            }
        
        # Prepare successful response for Transfer Family
        response_body = {
            'Role': user_data['role_arn'],
            'HomeDirectory': user_data['home_directory'],
            'HomeDirectoryType': 'PATH',
            'Policy': json.dumps({
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Effect': 'Allow',
                        'Action': [
                            's3:ListBucket',
                            's3:GetBucketLocation'
                        ],
                        'Resource': f"arn:aws:s3:::{os.environ.get('S3_BUCKET', 'ftp-files-bucket-9824')}"
                    },
                    {
                        'Effect': 'Allow',
                        'Action': [
                            's3:GetObject',
                            's3:PutObject',
                            's3:DeleteObject'
                        ],
                        'Resource': f"arn:aws:s3:::{os.environ.get('S3_BUCKET', 'ftp-files-bucket-9824')}/*"
                    }
                ]
            })
        }
        
        logger.info(f"Authentication successful for user: {username}")
        
        conn.close()
        
        return {
            'statusCode': 200,
            'body': json.dumps(response_body)
        }
        
    except Exception as e:
        logger.error(f"Authentication handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error'
            })
        } 