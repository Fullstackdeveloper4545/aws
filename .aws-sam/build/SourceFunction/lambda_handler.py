import json
import os
import uuid
import logging
import boto3
import csv
import io
from datetime import datetime
from typing import List, Dict, Optional
from db_manager import DBManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class S3Manager:
    """Manages S3 operations"""
    
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3')
    
    def download_file(self, key: str) -> Optional[str]:
        """Download file from S3 and return content as string"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            file_content = response['Body'].read().decode('utf-8')
            logger.info(f"Successfully downloaded file from S3: s3://{self.bucket_name}/{key}")
            return file_content
        except Exception as e:
            logger.error(f"Error downloading from S3: {str(e)}")
            return None
    
    def get_s3_location(self, key: str) -> str:
        """Get S3 location string"""
        return f"s3://{self.bucket_name}/{key}"

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

def parse_csv_to_json(csv_content: str, filename: str) -> List[Dict]:
    """Parse CSV content and convert to list of JSON objects"""
    try:
        # Use StringIO to create a file-like object for csv.DictReader
        csv_file = io.StringIO(csv_content)
        reader = csv.DictReader(csv_file)
        
        json_data = []
        for row in reader:
            # Clean up the row data (remove extra whitespace)
            cleaned_row = {key.strip(): value.strip() for key, value in row.items()}
            json_data.append(cleaned_row)
        
        logger.info(f"Successfully parsed CSV file {filename} into {len(json_data)} JSON objects")
        return json_data
    except Exception as e:
        logger.error(f"Error parsing CSV to JSON: {str(e)}")
        return []

def _validate_environment_variables() -> tuple[Optional[str], Optional[str]]:
    """Validate and return required environment variables"""
    s3_bucket = os.environ.get('S3_BUCKET')
    sqs_queue_url = os.environ.get('SQS_QUEUE_URL')
    
    if not all([s3_bucket, sqs_queue_url]):
        logger.error("Missing required environment variables: S3_BUCKET or SQS_QUEUE_URL")
        return None, None
    
    return s3_bucket, sqs_queue_url

def _extract_s3_records_from_sqs_body(sqs_body: Dict) -> List[Dict]:
    """Extract S3 records from SQS message body"""
    if 'Records' in sqs_body:
        # Direct S3 event
        return sqs_body['Records']
    else:
        # SQS message containing S3 event
        return [sqs_body]

def _should_process_file(key: str) -> bool:
    """Check if file should be processed based on its location"""
    return key.startswith('uploads/')

def _process_csv_file(file_content: str, key: str, unique_id: str, 
                     sqs_manager: SQSManager, db_manager: DBManager) -> bool:
    """Process CSV file and send individual rows to SQS"""
    json_data_list = parse_csv_to_json(file_content, key)
    if not json_data_list:
        logger.error(f"Failed to parse CSV file {key}")
        db_manager.update_status(unique_id, 'Failed')
        return False
    
    # Send each JSON object to SQS for transformer
    success_count = 0
    for i, json_data in enumerate(json_data_list):
        json_unique_id = f"{unique_id}_row_{i+1}"
        if sqs_manager.send_json_message(json_data, json_unique_id, key):
            success_count += 1
    
    if success_count > 0:
        db_manager.update_status(unique_id, 'Queued')
        logger.info(f"Successfully queued {success_count} JSON objects for file {key}")
        return True
    else:
        db_manager.update_status(unique_id, 'Failed')
        logger.error(f"Failed to queue any JSON objects for file {key}")
        return False

def _process_non_csv_file(file_content: str, key: str, unique_id: str,
                         sqs_manager: SQSManager, db_manager: DBManager) -> bool:
    """Process non-CSV file and send as simple JSON structure"""
    json_data = {
        'filename': key,
        'content': file_content,
        'file_type': 'text'
    }
    
    if sqs_manager.send_json_message(json_data, unique_id, key):
        db_manager.update_status(unique_id, 'Queued')
        return True
    else:
        db_manager.update_status(unique_id, 'Failed')
        return False

def _process_single_file(s3_record: Dict, s3_manager: S3Manager, 
                        sqs_manager: SQSManager, db_manager: DBManager) -> None:
    """Process a single S3 file record"""
    # Extract S3 object information
    bucket_name = s3_record['s3']['bucket']['name']
    key = s3_record['s3']['object']['key']
    
    # Only process files in the uploads/ directory
    if not _should_process_file(key):
        logger.info(f"Skipping file {key} - not in uploads/ directory")
        return
    
    unique_id = str(uuid.uuid4())
    s3_location = s3_manager.get_s3_location(key)
    
    logger.info(f"Processing S3 upload event for file: {key}")
    
    try:
        # Insert process as Pending
        db_manager.insert_process(unique_id, key, s3_location, 'Pending')
        
        # Download file from S3
        file_content = s3_manager.download_file(key)
        if file_content is None:
            logger.error(f"Failed to download file {key} from S3")
            db_manager.update_status(unique_id, 'Failed')
            return
        
        db_manager.update_status(unique_id, 'Downloaded')
        
        # Process file based on type
        success = False
        if key.endswith('.csv'):
            success = _process_csv_file(file_content, key, unique_id, sqs_manager, db_manager)
        else:
            success = _process_non_csv_file(file_content, key, unique_id, sqs_manager, db_manager)
        
        if success:
            logger.info(f"Successfully processed file: {key}")
        else:
            logger.error(f"Failed to process file: {key}")
            
    except Exception as e:
        logger.error(f"Error processing file {key}: {str(e)}")
        db_manager.update_status(unique_id, 'Failed')

def _process_sqs_record(record: Dict, s3_manager: S3Manager, 
                       sqs_manager: SQSManager, db_manager: DBManager) -> None:
    """Process a single SQS record containing S3 event information"""
    try:
        # Parse SQS message body (which contains S3 event)
        sqs_body = json.loads(record['body'])
        
        # Extract S3 event information
        s3_records = _extract_s3_records_from_sqs_body(sqs_body)
        
        for s3_record in s3_records:
            _process_single_file(s3_record, s3_manager, sqs_manager, db_manager)
            
    except Exception as e:
        logger.error(f"Error processing SQS record: {str(e)}")

def process_s3_upload_event(event: Dict) -> Dict:
    """Process S3 upload event and create JSON for transformer"""
    
    # Validate environment variables
    s3_bucket, sqs_queue_url = _validate_environment_variables()
    if not s3_bucket or not sqs_queue_url:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Missing required environment variables'})
        }
    
    # Initialize managers
    s3_manager = S3Manager(s3_bucket)
    sqs_manager = SQSManager(sqs_queue_url)
    db_manager = DBManager()
    
    try:
        # Process each SQS record (which contains S3 event)
        for record in event['Records']:
            _process_sqs_record(record, s3_manager, sqs_manager, db_manager)
    
    except Exception as e:
        logger.error(f"Error in process_s3_upload_event: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Successfully processed'
        })
    }

def lambda_handler(event, context):
    """AWS Lambda handler function for S3 upload events"""
    logger.info(f"FTP Listener Lambda started. Event: {json.dumps(event)}")
    
    try:
        result = process_s3_upload_event(event)
        logger.info(f"FTP Listener Lambda completed successfully: {result}")
        return result
    
    except Exception as e:
        logger.error(f"FTP Listener Lambda failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
