import os
import ssl
import json
import tempfile
import logging
from typing import Dict, Any, Optional, List
from django.conf import settings
from .models import BNSFCertificate, BNSFWaybill

logger = logging.getLogger(__name__)

class BNSFAPIClient:
    """Client for interacting with BNSF API"""
    
    def __init__(self, certificate: BNSFCertificate):
        self.certificate = certificate
        self.api_url = certificate.api_url
        self.skip_verify = certificate.skip_verify
        
    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context with client certificate"""
        context = ssl.create_default_context()
        
        if self.skip_verify:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            logger.warning("SSL verification is disabled - this should only be used in development")
        else:
            # Load server certificate for verification
            if self.certificate.server_cer:
                server_cert_path = self.certificate.server_cer.path
                context.load_verify_locations(server_cert_path)
        
        # Load client certificate
        if self.certificate.client_pfx:
            client_cert_path = self.certificate.client_pfx.path
            context.load_cert_chain(client_cert_path, password=self.certificate.pfx_password)
        
        return context
    
    def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with SSL context"""
        import urllib.request
        import urllib.parse
        import urllib.error
        
        # Create SSL context
        ssl_context = self._create_ssl_context()
        
        # Prepare request
        if 'data' in kwargs:
            if isinstance(kwargs['data'], dict):
                kwargs['data'] = json.dumps(kwargs['data']).encode('utf-8')
                kwargs.setdefault('headers', {})['Content-Type'] = 'application/json'
        
        # Create request
        req = urllib.request.Request(url, **kwargs)
        
        # Make request with SSL context
        try:
            with urllib.request.urlopen(req, context=ssl_context) as response:
                response_data = response.read().decode('utf-8')
                return {
                    'status_code': response.status,
                    'data': json.loads(response_data) if response_data else {},
                    'headers': dict(response.headers)
                }
        except urllib.error.HTTPError as e:
            error_data = e.read().decode('utf-8') if e.fp else 'No error details'
            logger.error(f"HTTP Error {e.code}: {error_data}")
            return {
                'status_code': e.code,
                'data': {'error': error_data},
                'headers': dict(e.headers) if hasattr(e, 'headers') else {}
            }
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            return {
                'status_code': 0,
                'data': {'error': str(e)},
                'headers': {}
            }
    
    def fetch_waybill(self, equipment_initial: str, equipment_number: str) -> Dict[str, Any]:
        """Fetch waybill data for specific equipment"""
        url = f"{self.api_url}/{equipment_initial}/{equipment_number}"
        
        logger.info(f"Fetching waybill for {equipment_initial}{equipment_number}")
        
        response = self._make_request('GET', url)
        
        if response['status_code'] == 200:
            logger.info(f"Successfully fetched waybill for {equipment_initial}{equipment_number}")
            return {
                'success': True,
                'data': response['data'],
                'equipment_initial': equipment_initial,
                'equipment_number': equipment_number
            }
        else:
            logger.error(f"Failed to fetch waybill: {response['data']}")
            return {
                'success': False,
                'error': response['data'].get('error', 'Unknown error'),
                'status_code': response['status_code']
            }
    
    def fetch_all_cars(self) -> Dict[str, Any]:
        """Fetch all cars data"""
        url = self.api_url
        
        logger.info(f"Fetching all cars from {url}")
        
        response = self._make_request('GET', url)
        
        if response['status_code'] == 200:
            logger.info("Successfully fetched all cars data")
            return {
                'success': True,
                'data': response['data']
            }
        else:
            logger.error(f"Failed to fetch all cars: {response['data']}")
            return {
                'success': False,
                'error': response['data'].get('error', 'Unknown error'),
                'status_code': response['status_code']
            }

class BNSFDataProcessor:
    """Process and store BNSF data"""
    
    @staticmethod
    def save_waybill(waybill_data: Dict[str, Any], equipment_initial: str, equipment_number: str) -> BNSFWaybill:
        """Save waybill data to database"""
        waybill = BNSFWaybill.objects.create(
            equipment_initial=equipment_initial,
            equipment_number=equipment_number,
            waybill_data=waybill_data
        )
        logger.info(f"Saved waybill for {equipment_initial}{equipment_number}")
        return waybill
    
    @staticmethod
    def get_waybill_data(waybill_id: int) -> Optional[BNSFWaybill]:
        """Get waybill data by ID"""
        try:
            return BNSFWaybill.objects.get(id=waybill_id)
        except BNSFWaybill.DoesNotExist:
            return None
    
    @staticmethod
    def get_all_waybills() -> List[BNSFWaybill]:
        """Get all waybills"""
        return list(BNSFWaybill.objects.all().order_by('-processed_at'))
    
    @staticmethod
    def get_waybills_count() -> int:
        """Get total count of waybills"""
        return BNSFWaybill.objects.count()

class BNSFDataFetcher:
    """Main class for fetching BNSF data"""
    
    def __init__(self, certificate_id: int):
        try:
            self.certificate = BNSFCertificate.objects.get(id=certificate_id, is_active=True)
            self.client = BNSFAPIClient(self.certificate)
            self.processor = BNSFDataProcessor()
        except BNSFCertificate.DoesNotExist:
            raise ValueError(f"Certificate with ID {certificate_id} not found or inactive")
    
    def fetch_single_waybill(self, equipment_initial: str, equipment_number: str) -> Dict[str, Any]:
        """Fetch single waybill and save to database"""
        result = self.client.fetch_waybill(equipment_initial, equipment_number)
        
        if result['success']:
            # Save to database
            waybill = self.processor.save_waybill(
                result['data'],
                equipment_initial,
                equipment_number
            )
            result['waybill_id'] = waybill.id
        
        return result
    
    def fetch_all_cars(self) -> Dict[str, Any]:
        """Fetch all cars data"""
        return self.client.fetch_all_cars()
    
    def get_waybills(self) -> List[BNSFWaybill]:
        """Get all waybills from database"""
        return self.processor.get_all_waybills()
    
    def get_waybill_data(self, waybill_id: int) -> Optional[BNSFWaybill]:
        """Get specific waybill data"""
        return self.processor.get_waybill_data(waybill_id)
