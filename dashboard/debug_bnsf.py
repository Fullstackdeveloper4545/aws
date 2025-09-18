#!/usr/bin/env python3
"""
Debug script for BNSF API integration
Run this script to test BNSF certificate handling and API calls
"""

import os
import sys
import django
import logging

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard.settings')
django.setup()

from core.models import BNSFCertificate, BNSFWaybill
from core.bnsf_integration import BNSFDataFetcher

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_certificate_upload():
    """Test certificate upload and validation"""
    print("=== Testing Certificate Upload ===")
    
    # Check if any certificates exist
    certificates = BNSFCertificate.objects.all()
    print(f"Found {certificates.count()} certificates in database")
    
    for cert in certificates:
        print(f"\nCertificate: {cert.name}")
        print(f"  - ID: {cert.id}")
        print(f"  - Active: {cert.is_active}")
        print(f"  - API URL: {cert.api_url}")
        print(f"  - Skip Verify: {cert.skip_verify}")
        print(f"  - Client PFX: {cert.client_pfx.name if cert.client_pfx else 'None'}")
        print(f"  - Server CER: {cert.server_cer.name if cert.server_cer else 'None'}")
        print(f"  - PFX Password: {'***' if cert.pfx_password else 'None'}")
        
        # Check if files exist
        if cert.client_pfx:
            pfx_path = cert.client_pfx.path
            print(f"  - PFX File exists: {os.path.exists(pfx_path)}")
            if os.path.exists(pfx_path):
                print(f"  - PFX File size: {os.path.getsize(pfx_path)} bytes")
        
        if cert.server_cer:
            cer_path = cert.server_cer.path
            print(f"  - CER File exists: {os.path.exists(cer_path)}")
            if os.path.exists(cer_path):
                print(f"  - CER File size: {os.path.getsize(cer_path)} bytes")

def test_bnsf_fetcher():
    """Test BNSF data fetcher"""
    print("\n=== Testing BNSF Data Fetcher ===")
    
    # Get first active certificate
    certificate = BNSFCertificate.objects.filter(is_active=True).first()
    if not certificate:
        print("❌ No active certificate found. Please upload a certificate first.")
        return False
    
    print(f"Using certificate: {certificate.name}")
    
    try:
        # Initialize fetcher
        fetcher = BNSFDataFetcher(certificate.id)
        print("✅ BNSFDataFetcher initialized successfully")
        
        # Test single waybill fetch (use a test equipment number)
        print("\nTesting single waybill fetch...")
        result = fetcher.fetch_single_waybill("TEST", "123456")
        
        if result['success']:
            print("✅ Single waybill fetch successful")
            print(f"  - Waybill ID: {result.get('waybill_id')}")
        else:
            print(f"❌ Single waybill fetch failed: {result.get('error')}")
        
        # Test all cars fetch
        print("\nTesting all cars fetch...")
        result = fetcher.fetch_all_cars()
        
        if result['success']:
            print("✅ All cars fetch successful")
            data = result.get('data', {})
            print(f"  - Data type: {type(data)}")
            if isinstance(data, dict):
                print(f"  - Data keys: {list(data.keys())}")
            elif isinstance(data, list):
                print(f"  - Data length: {len(data)}")
        else:
            print(f"❌ All cars fetch failed: {result.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing BNSF fetcher: {str(e)}")
        logger.exception("Full error details:")
        return False

def test_waybill_storage():
    """Test waybill storage and retrieval"""
    print("\n=== Testing Waybill Storage ===")
    
    waybills = BNSFWaybill.objects.all()
    print(f"Found {waybills.count()} waybills in database")
    
    for waybill in waybills[:5]:  # Show first 5
        print(f"\nWaybill: {waybill.equipment_initial}{waybill.equipment_number}")
        print(f"  - ID: {waybill.id}")
        print(f"  - Processed: {waybill.processed_at}")
        print(f"  - Data keys: {list(waybill.waybill_data.keys()) if isinstance(waybill.waybill_data, dict) else 'Not a dict'}")

def main():
    """Main debug function"""
    print("BNSF API Integration Debug Script")
    print("=" * 50)
    
    try:
        # Test certificate upload
        test_certificate_upload()
        
        # Test BNSF fetcher
        test_bnsf_fetcher()
        
        # Test waybill storage
        test_waybill_storage()
        
        print("\n" + "=" * 50)
        print("Debug script completed")
        
    except Exception as e:
        print(f"❌ Fatal error in debug script: {str(e)}")
        logger.exception("Full error details:")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
