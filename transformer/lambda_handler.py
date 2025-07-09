import json
import os
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional
from db_manager import DBManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class APIManager:
    """Manages external API operations"""
    
    def __init__(self, api_endpoint: str):
        self.api_endpoint = api_endpoint
        self.timeout = int(os.environ.get('API_TIMEOUT', '30'))
        self.headers = self._build_headers()
    
    def _build_headers(self) -> Dict[str, str]:
        """Build headers for API requests"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Marium-Transformer/1.0'
        }
        
        # Add any additional headers from environment variables
        api_headers = os.environ.get('API_HEADERS')
        if api_headers:
            try:
                additional_headers = json.loads(api_headers)
                headers.update(additional_headers)
            except json.JSONDecodeError:
                logger.warning(f"Invalid API_HEADERS environment variable: {api_headers}")
        
        return headers
    
    def send_json_data(self, json_data: Dict, unique_id: str, original_file: str) -> Dict:
        """
        Send JSON data to external API.
        
        Args:
            json_data: The JSON data to send
            unique_id: The unique ID for tracking
            original_file: The original file name for context
        
        Returns:
            Dictionary with success status, status code, response, and error info
        """
        # Add request-specific headers
        request_headers = self.headers.copy()
        request_headers.update({
            'X-Request-ID': unique_id,
            'X-Source-File': original_file
        })
        
        try:
            # Make the API request
            response = requests.post(
                self.api_endpoint,
                json=json_data,
                headers=request_headers,
                timeout=self.timeout
            )
            
            # Log the API call details
            logger.info(f"API call for ID {unique_id}: Status {response.status_code}")
            
            # Check if the request was successful
            if response.status_code >= 200 and response.status_code < 300:
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'response': response.text,
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'response': None,
                    'error': f"API returned status code {response.status_code}: {response.text}"
                }
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error for ID {unique_id}: {error_msg}")
            return {
                'success': False,
                'status_code': 0,
                'response': None,
                'error': error_msg
            }

def _validate_environment_variables() -> Optional[str]:
    """Validate and return required environment variables"""
    api_endpoint = os.environ.get('API_ENDPOINT')
    
    if not api_endpoint:
        logger.error("API_ENDPOINT environment variable not set")
        return None
    
    return api_endpoint

def _parse_sqs_message(record: Dict) -> Optional[Dict]:
    """Parse SQS message and extract required fields"""
    try:
        message_body = json.loads(record['body'])
        
        # Validate required fields
        required_fields = ['json_data', 'unique_id', 'original_file']
        for field in required_fields:
            if field not in message_body:
                logger.error(f"Missing required field in SQS message: {field}")
                return None
        
        # Add timestamp if not present
        if 'timestamp' not in message_body:
            message_body['timestamp'] = datetime.utcnow().isoformat()
        
        return message_body
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing SQS message: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing SQS message: {str(e)}")
        return None

def _process_single_message(message_data: Dict, api_manager: APIManager, 
                          db_manager: DBManager) -> Dict:
    """Process a single SQS message"""
    unique_id = message_data['unique_id']
    original_file = message_data['original_file']
    json_data = message_data['json_data']
    
    try:
        # Update status to Processing
        db_manager.update_status(unique_id, 'Processing')
        logger.info(f"Processing JSON data for file: {original_file} with ID: {unique_id}")
        
        # Send JSON data to external API
        api_response = api_manager.send_json_data(json_data, unique_id, original_file)
        
        # Store API call details in database
        db_manager.insert_api_call(
            unique_id, 
            json_data, 
            api_response['status_code'], 
            api_response['response'] if api_response['success'] else None,
            api_response['error'] if not api_response['success'] else None
        )
        db_manager.update_status(unique_id, 'Processed')

        if api_response['success']:
            return {
                'unique_id': unique_id,
                'original_file': original_file,
                'status': 'success',
                'api_status': api_response['status_code'],
                'api_response': api_response['response']
            }
        else:
            logger.error(f"Failed to send JSON data to API for ID: {unique_id}")
            return {
                'unique_id': unique_id,
                'original_file': original_file,
                'status': 'failed',
                'error': api_response['error']
            }
        
    except Exception as e:
        logger.error(f"Error processing message for ID {unique_id}: {str(e)}")
        return {
            'unique_id': unique_id,
            'original_file': original_file,
            'status': 'failed',
            'error': str(e)
        }

def _process_sqs_record(record: Dict, api_manager: APIManager, 
                       db_manager: DBManager) -> Optional[Dict]:
    """Process a single SQS record"""
    # Parse SQS message
    message_data = _parse_sqs_message(record)
    if not message_data:
        return {
            'unique_id': 'unknown',
            'original_file': 'unknown',
            'status': 'failed',
            'error': 'Failed to parse SQS message'
        }
    
    return _process_single_message(message_data, api_manager, db_manager)

def process_sqs_messages(event: Dict) -> Dict:
    """Process SQS messages and send JSON data to external API"""
    
    # Validate environment variables
    api_endpoint = _validate_environment_variables()
    if not api_endpoint:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'API_ENDPOINT environment variable not set'})
        }
    
    # Initialize managers
    api_manager = APIManager(api_endpoint)
    db_manager = DBManager()
    
    try:
        # Process each SQS record
        for record in event['Records']:
            _process_sqs_record(record, api_manager, db_manager)
    
    except Exception as e:
        logger.error(f"Error in process_sqs_messages: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    
    logger.info("Transformer completed")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Successfully processed'
        })
    }

def lambda_handler(event, context):
    """AWS Lambda handler function for processing SQS messages"""
    logger.info(f"Transformer Lambda started. Event: {json.dumps(event)}")
    
    try:
        result = process_sqs_messages(event)
        logger.info(f"Transformer Lambda completed successfully: {result}")
        return result
    
    except Exception as e:
        logger.error(f"Transformer Lambda failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }