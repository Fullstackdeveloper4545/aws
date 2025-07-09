import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json

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
                
                cur.execute(full_query, all_values)
        finally:
            conn.close()

    @staticmethod
    def insert_process(unique_id, filename, s3_location, status):
        query = """
            INSERT INTO file_processes (unique_id, filename, s3_location, status)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (unique_id) DO NOTHING;
        """
        values = (unique_id, filename, s3_location, status)
        DBManager.execute_query(query, values)

    @staticmethod
    def update_status(unique_id, status):
        query = "UPDATE file_processes SET status = %s"
        values = (status,)
        where_clause = "WHERE unique_id = %s"
        where_values = (unique_id,)
        DBManager.execute_query(query, values, where_clause, where_values)

    @staticmethod
    def update_s3_location(unique_id, s3_location):
        query = "UPDATE file_processes SET s3_location = %s"
        values = (s3_location,)
        where_clause = "WHERE unique_id = %s"
        where_values = (unique_id,)
        DBManager.execute_query(query, values, where_clause, where_values)

    @staticmethod
    def insert_api_call(unique_id, row_number, json_payload, api_status, api_response=None, error_message=None):
        query = """
            INSERT INTO api_calls (unique_id, row_number, json_payload, api_status, api_response, error_message, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW());
        """
        values = (unique_id, row_number, json.dumps(json_payload), api_status, api_response, error_message)
        DBManager.execute_query(query, values)
    
    def __init__(self):
        pass
    