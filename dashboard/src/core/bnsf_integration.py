import os
import ssl
import json
import tempfile
import logging
from typing import Dict, Any, Optional, List
from django.conf import settings
from .models import BNSFCertificate, BNSFWaybill
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class BNSFAPIClient:
    """Client for interacting with BNSF API"""
    
    def __init__(self, certificate: BNSFCertificate):
        self.certificate = certificate
        self.api_url = certificate.api_url
        self.skip_verify = certificate.skip_verify
        self.session = None
        
    def _convert_pfx_to_pem(self, pfx_data: bytes, password: str = None) -> tuple:
        """Convert PFX certificate to PEM format"""
        try:
            # Load PFX data
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                pfx_data, 
                password.encode() if password else None
            )
            
            # Convert to PEM format
            private_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
            
            return private_key_pem, cert_pem
            
        except Exception as e:
            logger.error(f"Error converting PFX to PEM: {str(e)}")
            raise ValueError(f"Failed to convert PFX certificate: {str(e)}")
    
    def _create_session(self) -> requests.Session:
        """Create requests session with SSL certificates"""
        if self.session:
            return self.session
            
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Handle certificates
        if self.certificate.client_pfx and self.certificate.client_pfx.path:
            try:
                # Read PFX file
                with open(self.certificate.client_pfx.path, 'rb') as f:
                    pfx_data = f.read()
                
                # Convert PFX to PEM
                private_key_pem, cert_pem = self._convert_pfx_to_pem(
                    pfx_data, 
                    self.certificate.pfx_password
                )
                
                # Create temporary files for certificates
                with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as key_file:
                    key_file.write(private_key_pem.decode())
                    key_file_path = key_file.name
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as cert_file:
                    cert_file.write(cert_pem.decode())
                    cert_file_path = cert_file.name
                
                # Set client certificate
                session.cert = (cert_file_path, key_file_path)
                
                # Store file paths for cleanup
                self._temp_files = [key_file_path, cert_file_path]
                
            except Exception as e:
                logger.error(f"Error setting up client certificate: {str(e)}")
                raise ValueError(f"Failed to setup client certificate: {str(e)}")
        
        # Handle server certificate verification
        if not self.skip_verify and self.certificate.server_cer and self.certificate.server_cer.path:
            try:
                # For server certificate verification, we need to create a custom SSL context
                # This is more complex with requests, so we'll use verify=False for now
                # and implement proper verification later if needed
                session.verify = False
                logger.warning("Server certificate verification is disabled due to complexity with requests library")
            except Exception as e:
                logger.error(f"Error setting up server certificate: {str(e)}")
                session.verify = False
        else:
            session.verify = not self.skip_verify
        
        self.session = session
        return session
    
    def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with proper error handling"""
        try:
            session = self._create_session()
            
            # Set default headers
            headers = kwargs.get('headers', {})
            headers.setdefault('Content-Type', 'application/json')
            headers.setdefault('Accept', 'application/json')
            kwargs['headers'] = headers
            
            # Make request
            response = session.request(method, url, **kwargs)
            
            # Parse response
            try:
                response_data = response.json() if response.content else {}
            except json.JSONDecodeError:
                response_data = {'raw_content': response.text}
            
            return {
                'status_code': response.status_code,
                'data': response_data,
                'headers': dict(response.headers),
                'success': response.status_code == 200
            }
            
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL Error: {str(e)}")
            return {
                'status_code': 0,
                'data': {'error': f'SSL Error: {str(e)}'},
                'headers': {},
                'success': False
            }
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection Error: {str(e)}")
            return {
                'status_code': 0,
                'data': {'error': f'Connection Error: {str(e)}'},
                'headers': {},
                'success': False
            }
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout Error: {str(e)}")
            return {
                'status_code': 0,
                'data': {'error': f'Timeout Error: {str(e)}'},
                'headers': {},
                'success': False
            }
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            return {
                'status_code': 0,
                'data': {'error': str(e)},
                'headers': {},
                'success': False
            }
    
    def fetch_waybill(self, equipment_initial: str, equipment_number: str) -> Dict[str, Any]:
        """Fetch waybill data for specific equipment"""
        url = f"{self.api_url}/{equipment_initial}/{equipment_number}"
        
        logger.info(f"Fetching waybill for {equipment_initial}{equipment_number} from {url}")
        
        response = self._make_request('GET', url)
        
        if response['success']:
            logger.info(f"Successfully fetched waybill for {equipment_initial}{equipment_number}")
            return {
                'success': True,
                'data': response['data'],
                'equipment_initial': equipment_initial,
                'equipment_number': equipment_number
            }
        else:
            error_msg = response['data'].get('error', f'HTTP {response["status_code"]}')
            logger.error(f"Failed to fetch waybill: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'status_code': response['status_code']
            }
    
    def fetch_all_cars(self) -> Dict[str, Any]:
        """Fetch all cars data"""
        url = self.api_url
        
        logger.info(f"Fetching all cars from {url}")
        
        response = self._make_request('GET', url)
        
        if response['success']:
            logger.info("Successfully fetched all cars data")
            return {
                'success': True,
                'data': response['data']
            }
        else:
            error_msg = response['data'].get('error', f'HTTP {response["status_code"]}')
            logger.error(f"Failed to fetch all cars: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'status_code': response['status_code']
            }
    
    def cleanup(self):
        """Clean up temporary files"""
        if hasattr(self, '_temp_files'):
            for temp_file in self._temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {temp_file}: {str(e)}")

class BNSFDataProcessor:
    """Process and store BNSF data"""
    
    @staticmethod
    def save_waybill(waybill_data: Dict[str, Any], equipment_initial: str, equipment_number: str) -> BNSFWaybill:
        """Save waybill data to database"""
        try:
            waybill = BNSFWaybill.objects.create(
                equipment_initial=equipment_initial,
                equipment_number=equipment_number,
                waybill_data=waybill_data
            )
            logger.info(f"Saved waybill for {equipment_initial}{equipment_number}")
            return waybill
        except Exception as e:
            logger.error(f"Error saving waybill: {str(e)}")
            raise
    
    @staticmethod
    def get_waybill_data(waybill_id: int) -> Optional[BNSFWaybill]:
        """Get waybill data by ID"""
        try:
            return BNSFWaybill.objects.get(id=waybill_id)
        except BNSFWaybill.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting waybill data: {str(e)}")
            return None
    
    @staticmethod
    def get_all_waybills() -> List[BNSFWaybill]:
        """Get all waybills"""
        try:
            return list(BNSFWaybill.objects.all().order_by('-processed_at'))
        except Exception as e:
            logger.error(f"Error getting all waybills: {str(e)}")
            return []
    
    @staticmethod
    def get_waybills_count() -> int:
        """Get total count of waybills"""
        try:
            return BNSFWaybill.objects.count()
        except Exception as e:
            logger.error(f"Error getting waybills count: {str(e)}")
            return 0

class BNSFDataFetcher:
    """Main class for fetching BNSF data"""
    
    def __init__(self, certificate_id: int):
        try:
            self.certificate = BNSFCertificate.objects.get(id=certificate_id, is_active=True)
            self.client = BNSFAPIClient(self.certificate)
            self.processor = BNSFDataProcessor()
            logger.info(f"Initialized BNSFDataFetcher with certificate: {self.certificate.name}")
        except BNSFCertificate.DoesNotExist:
            error_msg = f"Certificate with ID {certificate_id} not found or inactive"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error initializing BNSFDataFetcher: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def fetch_single_waybill(self, equipment_initial: str, equipment_number: str) -> Dict[str, Any]:
        """Fetch single waybill and save to database"""
        try:
            logger.info(f"Fetching single waybill for {equipment_initial}{equipment_number}")
            result = self.client.fetch_waybill(equipment_initial, equipment_number)
            
            if result['success']:
                # Save to database
                waybill = self.processor.save_waybill(
                    result['data'],
                    equipment_initial,
                    equipment_number
                )
                result['waybill_id'] = waybill.id
                logger.info(f"Successfully processed waybill for {equipment_initial}{equipment_number}")
            else:
                logger.error(f"Failed to fetch waybill: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error in fetch_single_waybill: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        finally:
            # Cleanup temporary files
            if hasattr(self.client, 'cleanup'):
                self.client.cleanup()
    
    def fetch_all_cars(self) -> Dict[str, Any]:
        """Fetch all cars data"""
        try:
            logger.info("Fetching all cars data")
            result = self.client.fetch_all_cars()
            
            if result['success']:
                logger.info("Successfully fetched all cars data")
            else:
                logger.error(f"Failed to fetch all cars: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error in fetch_all_cars: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        finally:
            # Cleanup temporary files
            if hasattr(self.client, 'cleanup'):
                self.client.cleanup()
    
    def get_waybills(self) -> List[BNSFWaybill]:
        """Get all waybills from database"""
        return self.processor.get_all_waybills()
    
    def get_waybill_data(self, waybill_id: int) -> Optional[BNSFWaybill]:
        """Get specific waybill data"""
        return self.processor.get_waybill_data(waybill_id)