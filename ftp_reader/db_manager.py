import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import logging

logger = logging.getLogger()

class DBManager:
    @staticmethod
    def get_connection():
        return psycopg2.connect(
            host=os.environ['PG_HOST'],
            port=os.environ.get('PG_PORT', 5432),
            dbname=os.environ['PG_DB'],
            user=os.environ['PG_USER'],
            password=os.environ['PG_PASSWORD']
        )

    @staticmethod
    def execute_query(query, values=None, where_clause=None, where_values=None):
        conn = DBManager.get_connection()
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                if where_clause and where_values:
                    full_query = f"{query} {where_clause}"
                    all_values = values + where_values if values else where_values
                else:
                    full_query = query
                    all_values = values
                logger.info(f"Executing query: {full_query} with values: {all_values}")
                cur.execute(full_query, all_values)
        finally:
            conn.close()

    @staticmethod
    def get_recipient_emails():
        """Get list of recipient emails from email_configs table"""
        try:
            conn = DBManager.get_connection()
            with conn.cursor() as cur:
                query = "SELECT email FROM email_configs WHERE email IS NOT NULL"
                cur.execute(query)
                results = cur.fetchall()
                return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Error getting emails from database: {str(e)}")
            return []
        finally:
            conn.close()

    @staticmethod
    def insert_process(unique_id, filename, location, status):
        query = """
            INSERT INTO file_processes (unique_id, filename, location, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (unique_id) DO NOTHING;
        """
        values = (unique_id, filename, location, status)
        DBManager.execute_query(query, values)

    @staticmethod
    def update_status(unique_id, status, error_message=None, site_id=None):
        query = "UPDATE file_processes SET status = %s, updated_at = NOW()"
        values = (status,)
        if error_message:
            query += ", error_message = %s"
            values += (error_message,)
        if site_id:
            query += ", site_id = %s"
            values += (site_id,)
        where_clause = "WHERE unique_id = %s"
        where_values = (unique_id,)
        DBManager.execute_query(query, values, where_clause, where_values)

    @staticmethod
    def update_location(unique_id, location):
        query = "UPDATE file_processes SET location = %s, updated_at = NOW()"
        values = (location,)
        where_clause = "WHERE unique_id = %s"
        where_values = (unique_id,)
        DBManager.execute_query(query, values, where_clause, where_values)

    @staticmethod
    def insert_api_call(unique_id, json_payload, api_status, api_response=None, error_message=None):
        query = """
            INSERT INTO api_calls (unique_id, json_payload, api_status, api_response, error_message, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW());
        """
        values = (unique_id, json.dumps(json_payload), api_status, api_response, error_message)
        DBManager.execute_query(query, values)

    @staticmethod
    def get_processed_files(hours_back: int = 24):
        """Get list of files that have been processed in the last N hours"""
        try:
            conn = DBManager.get_connection()
            with conn.cursor() as cur:
                query = """
                    SELECT DISTINCT filename 
                    FROM file_processes 
                    WHERE created_at >= NOW() - INTERVAL '%s hours'
                    AND status IN ('Queued', 'Processed', 'Failed')
                """
                cur.execute(query, (hours_back,))
                results = cur.fetchall()
                return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Error getting processed files: {str(e)}")
            return []
        finally:
            conn.close()
    
    def __init__(self):
        pass 