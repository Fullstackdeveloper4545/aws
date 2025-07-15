import json
import os
import uuid
import logging
import boto3
import csv
import io
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import urllib.parse
from db_manager import DBManager
from train_data_parser import parse_train_data_to_json
from ftp_manager import FTPManager
from email_manager import EmailManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class SQSManager:
    """Manages SQS operations"""
    
    def __init__(self, queue_url: str):
        self.queue_url = queue_url
        self.sqs_client = boto3.client('sqs')
    
    def send_json_message(self, json_data: Dict, unique_id: str, original_file: str) -> bool:
        """Send JSON data to SQS queue for transformer"""
        try:
            message_body = {
                'json_data': json_data,
                'unique_id': unique_id,
                'original_file': original_file,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body)
            )
            logger.info(f"Sent JSON message to SQS for file {original_file} with ID {unique_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to SQS: {str(e)}")
            return False

def _validate_environment_variables() -> tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[int], Optional[str], Optional[str]]:
    """Validate and return required environment variables"""
    ftp_host = os.environ.get('FTP_HOST')
    ftp_username = os.environ.get('FTP_USERNAME')
    ftp_password = os.environ.get('FTP_PASSWORD')
    ftp_port = int(os.environ.get('FTP_PORT', 21))
    sqs_queue_url = os.environ.get('SQS_QUEUE_URL')
    source_folder = os.environ.get('FTP_SOURCE_FOLDER', 'uploads')
    dest_folder = os.environ.get('FTP_DEST_FOLDER', 'processed')
    
    if not all([ftp_host, ftp_username, ftp_password, sqs_queue_url]):
        logger.error("Missing required environment variables: FTP_HOST, FTP_USERNAME, FTP_PASSWORD, or SQS_QUEUE_URL")
        return None, None, None, None, None, None, None, None
    
    return ftp_host, ftp_username, ftp_password, sqs_queue_url, ftp_port, source_folder, dest_folder

def _process_data_file(file_content: str, filename: str, unique_id: str, 
                      sqs_manager: SQSManager, db_manager: DBManager, email_manager: EmailManager) -> bool:
    """Process train data file and send individual JSON objects to SQS"""
    site_id = None
    try:
        # Parse as train data (asterisk-delimited format)
        json_data = parse_train_data_to_json(file_content, filename)
        site_id = json_data.get('siteID')
        sqs_manager.send_json_message(json_data, unique_id, filename)
        db_manager.update_status(unique_id, 'Queued', site_id=site_id)
        logger.info(f"Successfully queued JSON objects for file {filename}")
        return True    
            
    except ValueError as e:
        # Handle filename validation errors
        error_msg = f"Filename validation failed for {filename}: {str(e)}"
        logger.error(error_msg)
        db_manager.update_status(unique_id, 'Failed', error_message=str(e), site_id=site_id)
        
        # Send failure notification
        email_manager.send_failure_notification(filename, str(e), unique_id, site_id)
        return False
    except Exception as e:
        # Handle other parsing errors
        error_msg = f"Unexpected error processing train data file {filename}: {str(e)}"
        logger.error(error_msg)
        db_manager.update_status(unique_id, 'Failed', error_message=str(e), site_id=site_id)
        
        # Send failure notification
        email_manager.send_failure_notification(filename, str(e), unique_id, site_id)
        return False

def _move_and_process_file(file_info: Dict, ftp_manager: FTPManager, 
                          sqs_manager: SQSManager, db_manager: DBManager,
                          email_manager: EmailManager, source_folder: str, dest_folder: str) -> bool:
    """Move file to processed folder first, then read and process it"""
    filename = file_info['filename']
    logger.info(f"Moving and processing file {filename} from {source_folder} to {dest_folder}")
    
    unique_id = str(uuid.uuid4())
    ftp_location = f"ftp://{ftp_manager.host}/{source_folder}/{filename}"
    
    try:
        # Insert process as Pending
        db_manager.insert_process(unique_id, filename, ftp_location, 'Pending')
        
        # Step 1: Move file to processed folder first (to prevent concurrent processing)
        if not ftp_manager.move_file(filename, source_folder, dest_folder):
            error_msg = f"Failed to move file {filename} from {source_folder} to {dest_folder}"
            logger.error(error_msg)
            db_manager.update_status(unique_id, 'Failed', error_message=error_msg)
            
            # Send failure notification
            email_manager.send_failure_notification(filename, error_msg, unique_id)
            return False
        
        logger.info(f"Successfully moved file {filename} to {dest_folder} directory")
        
        # Step 2: Download file from processed folder
        file_content = ftp_manager.download_file(filename, dest_folder)
        if file_content is None:
            error_msg = f"Failed to download file {filename} from {dest_folder}"
            logger.error(error_msg)
            db_manager.update_status(unique_id, 'Failed', error_message=error_msg)
            
            # Send failure notification
            email_manager.send_failure_notification(filename, error_msg, unique_id)
            return False
        
        db_manager.update_status(unique_id, 'Downloaded')
        
        # Step 3: Process file
        success = _process_data_file(file_content, filename, unique_id, sqs_manager, db_manager, email_manager)
        
        if success:
            logger.info(f"Successfully processed file: {filename}")
            return True
        else:
            logger.error(f"Failed to process file: {filename}")
            return False
            
    except Exception as e:
        error_msg = f"Error processing file {filename}: {str(e)}"
        logger.error(error_msg)
        db_manager.update_status(unique_id, 'Failed', error_message=str(e))
        
        # Send failure notification
        email_manager.send_failure_notification(filename, str(e), unique_id)
        return False

def process_scheduled_files(event: Dict) -> Dict:
    """Process files based on scheduler trigger"""
    
    # Validate environment variables
    ftp_host, ftp_username, ftp_password, sqs_queue_url, ftp_port, source_folder, dest_folder = _validate_environment_variables()
    if not all([ftp_host, ftp_username, ftp_password, sqs_queue_url]):
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Missing required environment variables'})
        }
    
    # Initialize managers
    ftp_manager = FTPManager(ftp_host, ftp_username, ftp_password, ftp_port)
    sqs_manager = SQSManager(sqs_queue_url)
    db_manager = DBManager()
    email_manager = EmailManager()
    
    try:
        # Get configuration from event or use defaults
        max_files = event.get('max_files', 100)
        hours_back = event.get('hours_back', 24)
        
        logger.info(f"Starting scheduled file processing with source folder: '{source_folder}', dest folder: '{dest_folder}', max_files: {max_files}, hours_back: {hours_back}")
        
        # Connect to FTP server
        if not ftp_manager.connect():
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to connect to FTP server'})
            }
        
        try:
            # Get list of files from FTP source directory
            ftp_files = ftp_manager.list_files(source_folder)
            
            if not ftp_files:
                logger.info(f"No files found in FTP source directory: {source_folder}")
                return {
                    'statusCode': 200,
                    'body': json.dumps({'message': 'No files found to process'})
                }
            
            # Get list of already processed files
            processed_files = db_manager.get_processed_files(hours_back)
            logger.info(f"Found {len(processed_files)} already processed files in the last {hours_back} hours")
            
            # Filter out already processed files
            files_to_process = []
            for file_info in ftp_files:
                if file_info['filename'] not in processed_files:
                    files_to_process.append(file_info)
            
            logger.info(f"Found {len(files_to_process)} new files to process")
            
            # Process each file (move first, then process)
            processed_count = 0
            failed_count = 0
            failures = []
            
            for file_info in files_to_process:
                try:
                    success = _move_and_process_file(file_info, ftp_manager, sqs_manager, db_manager, email_manager, source_folder, dest_folder)
                    if success:
                        processed_count += 1
                    else:
                        failed_count += 1
                        # Collect failure info for batch notification
                        failures.append({
                            'filename': file_info['filename'],
                            'unique_id': str(uuid.uuid4()),  # This would need to be tracked properly
                            'error_message': 'Processing failed'
                        })
                except Exception as e:
                    logger.error(f"Error processing file {file_info['filename']}: {str(e)}")
                    failed_count += 1
                    failures.append({
                        'filename': file_info['filename'],
                        'unique_id': str(uuid.uuid4()),
                        'error_message': str(e)
                    })
            
            # Send batch failure notification if there are failures
            if failures and email_manager.enabled:
                email_manager.send_batch_failure_notification(failures)
            
            logger.info(f"Processing complete. Processed: {processed_count}, Failed: {failed_count}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Successfully processed scheduled files',
                    'processed_count': processed_count,
                    'failed_count': failed_count,
                    'total_files_found': len(ftp_files),
                    'new_files_processed': len(files_to_process),
                    'source_folder': source_folder,
                    'dest_folder': dest_folder
                })
            }
        
        finally:
            # Disconnect from FTP server
            ftp_manager.disconnect()
    
    except Exception as e:
        logger.error(f"Error in process_scheduled_files: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def lambda_handler(event, context):
    """AWS Lambda handler function for scheduled file processing"""
    logger.info(f"FTP Reader Lambda started. Event: {json.dumps(event)}")
    
    try:
        result = process_scheduled_files(event)
        logger.info(f"FTP Reader Lambda completed successfully: {result}")
        return result
    
    except Exception as e:
        logger.error(f"FTP Reader Lambda failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
