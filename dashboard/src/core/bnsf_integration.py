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
import shutil
import subprocess

logger = logging.getLogger(__name__)

class BNSFAPIClient:
    """Client for interacting with BNSF API"""
    
    def __init__(self, certificate: BNSFCertificate):
        self.certificate = certificate
        # Prefer specific endpoint overrides if present
        self.cars_api_url = certificate.cars_api_url or certificate.api_url
        self.waybill_api_url = certificate.waybill_api_url or certificate.api_url
        self.skip_verify = certificate.skip_verify
        self.session = None
        
    def _convert_pfx_to_pem(self, pfx_data: bytes, password: str = None) -> tuple:
        """Convert PFX certificate to PEM format"""
        try:
            # Normalize password
            normalized_password = None
            if password is not None:
                normalized_password = password.strip()
                if normalized_password == "":
                    normalized_password = None

            # Load PFX data (try provided password, then fallback to no password if it fails)
            try:
                private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                    pfx_data,
                    normalized_password.encode() if normalized_password else None
                )
            except Exception as inner:
                # Fallback attempt without password in case it is actually blank
                try:
                    private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                        pfx_data,
                        None
                    )
                except Exception:
                    raise inner
            
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
            # Fallback: try OpenSSL if available
            try:
                if shutil.which('openssl') is None:
                    raise RuntimeError('OpenSSL not installed')

                normalized_password = (password or '').strip()
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.pfx', delete=False) as pfx_tmp:
                    pfx_tmp.write(pfx_data)
                    pfx_path = pfx_tmp.name

                key_file = tempfile.NamedTemporaryFile(mode='r', suffix='.pem', delete=False)
                cert_file = tempfile.NamedTemporaryFile(mode='r', suffix='.pem', delete=False)
                key_file_path, cert_file_path = key_file.name, cert_file.name
                key_file.close(); cert_file.close()

                passin = f"pass:{normalized_password}" if normalized_password else 'pass:'
                # Extract private key
                subprocess.check_call([
                    'openssl', 'pkcs12', '-in', pfx_path, '-nocerts', '-nodes',
                    '-passin', passin, '-out', key_file_path
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                # Extract certificate
                subprocess.check_call([
                    'openssl', 'pkcs12', '-in', pfx_path, '-clcerts', '-nokeys',
                    '-passin', passin, '-out', cert_file_path
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                with open(key_file_path, 'rb') as kf:
                    private_key_pem = kf.read()
                with open(cert_file_path, 'rb') as cf:
                    cert_pem = cf.read()

                # Track for cleanup
                self._temp_files = getattr(self, '_temp_files', []) + [pfx_path, key_file_path, cert_file_path]
                return private_key_pem, cert_pem
            except Exception as e2:
                raise ValueError(
                    "Failed to convert PFX certificate: Invalid password or PKCS12 data, and OpenSSL fallback failed."
                ) from e2
    
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
        if self.certificate.server_cer and self.certificate.server_cer.path and not self.skip_verify:
            try:
                server_cert_path = self.certificate.server_cer.path
                # If server cert is DER (.cer), convert to PEM for requests
                needs_convert = False
                try:
                    with open(server_cert_path, 'rb') as scf:
                        content = scf.read(64)
                        if b'-----BEGIN' not in content:
                            needs_convert = True
                except Exception:
                    needs_convert = False

                if needs_convert and shutil.which('openssl'):
                    with open(server_cert_path, 'rb') as scf:
                        der_bytes = scf.read()
                    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pem', delete=False) as pem_tmp:
                        pem_path = pem_tmp.name
                    # Convert DER to PEM
                    try:
                        # Write DER to temp file and call openssl to convert
                        with tempfile.NamedTemporaryFile(mode='wb', suffix='.cer', delete=False) as der_tmp:
                            der_tmp.write(der_bytes)
                            der_path = der_tmp.name
                        subprocess.check_call([
                            'openssl', 'x509', '-inform', 'DER', '-in', der_path, '-outform', 'PEM', '-out', pem_path
                        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        self._temp_files = getattr(self, '_temp_files', []) + [der_path, pem_path]
                        server_cert_path = pem_path
                    except Exception as conv_err:
                        logger.warning(f"Failed to convert server cert to PEM, using as-is: {str(conv_err)}")

                session.verify = server_cert_path
                logger.info("Server certificate verification enabled using provided certificate")
            except Exception as e:
                logger.error(f"Error setting up server certificate verification: {str(e)}")
                session.verify = True
        else:
            # Either explicit skip or no server cert provided
            session.verify = not self.skip_verify
        
        self.session = session
        return session
    
    def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with proper error handling and 429 backoff"""
        try:
            session = self._create_session()

            # Set default headers
            headers = kwargs.get('headers', {})
            headers.setdefault('Content-Type', 'application/json')
            headers.setdefault('Accept', 'application/json')
            kwargs['headers'] = headers

            max_attempts = 5
            attempt = 0
            while True:
                attempt += 1
                response = session.request(method, url, **kwargs)

                # 429 handling with exponential backoff
                if response.status_code == 429 and attempt < max_attempts:
                    retry_after = response.headers.get('Retry-After')
                    base_wait = 30  # Start with 30 seconds
                    wait_seconds = min(120, base_wait * (2 ** (attempt - 1)))  # Exponential backoff: 30s, 60s, 120s (capped at 120s)
                    
                    try:
                        if retry_after:
                            wait_seconds = max(int(retry_after), wait_seconds)
                    except Exception:
                        pass
                    
                    logger.warning(f"Rate limited (429). Attempt {attempt}/{max_attempts}. Waiting {wait_seconds} seconds...")
                    import time
                    time.sleep(wait_seconds)
                    continue

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
        """Fetch waybill data for specific equipment.
        BNSF trial waybill API expects query params: ?equipmentInitial=XXX&equipmentNumber=YYYYY
        """
        base = self.waybill_api_url.rstrip('/')
        url = base  # Params will be attached by requests
        params = {
            'equipmentInitial': equipment_initial,
            'equipmentNumber': equipment_number,
        }
        
        logger.debug(f"Fetching waybill for {equipment_initial}{equipment_number} from {base} with params {params}")
        
        response = self._make_request('GET', url, params=params)
        
        if response['success']:
            logger.debug(f"Successfully fetched waybill for {equipment_initial}{equipment_number}")
            return {
                'success': True,
                'data': response['data'],
                'equipment_initial': equipment_initial,
                'equipment_number': equipment_number
            }
        else:
            # Check if it's a 429 error specifically
            status_code = response.get('status_code', 0)
            if status_code == 429:
                error_msg = f"Rate limited (429) for {equipment_initial}{equipment_number}"
                logger.warning(error_msg)
            else:
                error_msg = response['data'].get('error', f'HTTP {response["status_code"]}')
                logger.error(f"Failed to fetch waybill: {error_msg}")
            
            return {
                'success': False,
                'error': error_msg,
                'equipment_initial': equipment_initial,
                'equipment_number': equipment_number,
                'status_code': status_code
            }
    
    def fetch_all_cars(self) -> Dict[str, Any]:
        """Fetch all cars data"""
        url = self.cars_api_url
        
        logger.info(f"Fetching all cars from {url}")
        
        response = self._make_request('GET', url)
        
        if response['success']:
            logger.info("Successfully fetched all cars data")
            data = response['data']
            # Basic diagnostics to aid troubleshooting when payload shape is unexpected
            try:
                top_keys = list(data.keys()) if isinstance(data, dict) else None
                sample = None
                if isinstance(data, list) and data:
                    sample = list(data[0].keys()) if isinstance(data[0], dict) else type(data[0]).__name__
            except Exception:
                top_keys = None
                sample = None
            return {
                'success': True,
                'data': data,
                'diagnostics': {
                    'type': type(data).__name__,
                    'top_level_keys': top_keys,
                    'list_sample_keys': sample,
                }
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
    
    def _extract_equipment_pairs(self, cars_payload: Any) -> List[Dict[str, str]]:
        """Extract list of {equipment_initial, equipment_number} from cars payload.
        Tries multiple common field names to be resilient to schema differences.
        """
        pairs: List[Dict[str, str]] = []
        seen = set()

        def try_extract(obj: Any):
            if not isinstance(obj, dict):
                return
            candidates = [
                (obj.get('eqInit'), obj.get('eqNbr')),
                (obj.get('equipmentInitial'), obj.get('equipmentNumber')),
                (obj.get('initial'), obj.get('number')),
                (obj.get('carInitial'), obj.get('carNumber')),
            ]
            for init, num in candidates:
                if init and num:
                    key = f"{init}:{num}"
                    if key not in seen:
                        seen.add(key)
                        pairs.append({'equipment_initial': str(init).strip(), 'equipment_number': str(num).strip()})
            # Heuristic fallback: look for any keys that look like init/number
            if len(pairs) == 0:
                lower_map = {str(k).lower(): v for k, v in obj.items()}
                init_key = next((k for k in lower_map.keys() if 'init' in k or 'initial' in k), None)
                num_key = next((k for k in lower_map.keys() if 'nbr' in k or 'number' in k or 'num' in k), None)
                if init_key and num_key:
                    init = lower_map.get(init_key)
                    num = lower_map.get(num_key)
                    if init and num:
                        key = f"{init}:{num}"
                        if key not in seen:
                            seen.add(key)
                            pairs.append({'equipment_initial': str(init).strip(), 'equipment_number': str(num).strip()})

        def walk(node: Any):
            if isinstance(node, dict):
                try_extract(node)
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(cars_payload)
        return pairs

    def fetch_waybills_for_all_cars(self, max_workers: int = 8, limit: Optional[int] = None) -> Dict[str, Any]:
        """Fetch all cars, then fetch and store waybills for each in parallel.

        Returns summary with totals and errors.
        """
        try:
            cars_result = self.fetch_all_cars()
            if not cars_result.get('success'):
                return {'success': False, 'error': cars_result.get('error', 'Failed to fetch cars')}

            cars_payload = cars_result.get('data')
            pairs = self._extract_equipment_pairs(cars_payload)
            if limit is not None:
                pairs = pairs[: max(0, int(limit))]

            logger.info(f"Preparing to fetch waybills for {len(pairs)} cars")

            results: List[Dict[str, Any]] = []
            errors: List[Dict[str, Any]] = []

            # Parallelize waybill fetches
            from concurrent.futures import ThreadPoolExecutor, as_completed

            def _normalize(init_value: str, num_value: str) -> Dict[str, str]:
                try:
                    normalized_init = str(init_value).strip().upper()
                    # keep digits only for number
                    import re
                    normalized_num = re.sub(r"\D", "", str(num_value))
                    return { 'equipment_initial': normalized_init, 'equipment_number': normalized_num }
                except Exception:
                    return { 'equipment_initial': str(init_value).strip(), 'equipment_number': str(num_value).strip() }

            def _task(init_num: Dict[str, str]) -> Dict[str, Any]:
                try:
                    normalized = _normalize(init_num['equipment_initial'], init_num['equipment_number'])
                    r = self.fetch_single_waybill(normalized['equipment_initial'], normalized['equipment_number'])
                    r['equipment_initial'] = normalized['equipment_initial']
                    r['equipment_number'] = normalized['equipment_number']
                    return r
                except Exception as e:
                    return {'success': False, 'error': str(e), 'equipment_initial': init_num.get('equipment_initial'), 'equipment_number': init_num.get('equipment_number')}

            # Be gentle with the trial API (avoid 429): force sequential with adaptive delay
            safe_workers = 1

            if safe_workers == 1:
                # Sequential mode with adaptive pacing to avoid 429 on trial API
                import time
                consecutive_429_errors = 0
                base_delay = 3  # Start with 3 seconds between requests
                current_delay = base_delay
                
                for i, p in enumerate(pairs):
                    res = _task(p)
                    if res.get('success'):
                        results.append({'equipment_initial': res['equipment_initial'], 'equipment_number': res['equipment_number'], 'waybill_id': res.get('waybill_id')})
                        consecutive_429_errors = 0  # Reset counter on success
                        # Gradually reduce delay if we're doing well
                        if current_delay > base_delay:
                            current_delay = max(base_delay, current_delay - 0.5)
                    else:
                        error_msg = res.get('error', '')
                        if '429' in str(error_msg) or 'Rate limited' in str(error_msg):
                            consecutive_429_errors += 1
                            # Increase delay significantly on 429 errors
                            current_delay = min(60, base_delay * (2 ** consecutive_429_errors))  # Max 60 seconds
                            logger.warning(f"429 error #{consecutive_429_errors}. Increasing delay to {current_delay}s")
                            
                            # If we get too many consecutive 429 errors, pause for a longer time
                            if consecutive_429_errors >= 5:
                                logger.error(f"Too many consecutive 429 errors ({consecutive_429_errors}). Pausing for 5 minutes...")
                                time.sleep(300)  # 5 minute pause
                                consecutive_429_errors = 0  # Reset after long pause
                                current_delay = base_delay * 2  # Start with higher delay
                        else:
                            consecutive_429_errors = 0  # Reset for non-429 errors
                        
                        errors.append({'equipment_initial': res.get('equipment_initial'), 'equipment_number': res.get('equipment_number'), 'error': res.get('error')})
                    
                    # Log progress every 25 requests (more frequent logging)
                    if (i + 1) % 25 == 0:
                        success_rate = (len(results) / (i + 1)) * 100
                        logger.info(f"Processed {i + 1}/{len(pairs)} cars. Success: {len(results)} ({success_rate:.1f}%), Errors: {len(errors)}, Current delay: {current_delay}s")
                    
                    # Wait before next request
                    time.sleep(current_delay)
            else:
                from concurrent.futures import ThreadPoolExecutor, as_completed
                with ThreadPoolExecutor(max_workers=safe_workers) as executor:
                    future_map = {executor.submit(_task, p): p for p in pairs}
                    for fut in as_completed(future_map):
                        res = fut.result()
                        if res.get('success'):
                            results.append({'equipment_initial': res['equipment_initial'], 'equipment_number': res['equipment_number'], 'waybill_id': res.get('waybill_id')})
                        else:
                            errors.append({'equipment_initial': res.get('equipment_initial'), 'equipment_number': res.get('equipment_number'), 'error': res.get('error')})

            # Calculate success rate and 429 error rate
            success_rate = (len(results) / len(pairs)) * 100 if pairs else 0
            error_429_count = sum(1 for e in errors if '429' in str(e.get('error', '')) or 'Rate limited' in str(e.get('error', '')))
            error_429_rate = (error_429_count / len(pairs)) * 100 if pairs else 0
            
            summary = {
                'success': True,
                'total_pairs': len(pairs),
                'fetched': len(results),
                'failed': len(errors),
                'success_rate': round(success_rate, 2),
                'error_429_count': error_429_count,
                'error_429_rate': round(error_429_rate, 2),
                'saved_waybill_ids': [r.get('waybill_id') for r in results if r.get('waybill_id') is not None],
                'cars_diagnostics': cars_result.get('diagnostics'),
                'sample_pairs': pairs[:5],
                'errors': errors[:20],  # cap
            }
            logger.info(f"Waybill fetch summary: {summary['fetched']} succeeded ({success_rate:.1f}%), {summary['failed']} failed, {error_429_count} were 429 errors ({error_429_rate:.1f}%)")
            return summary

        except Exception as e:
            logger.error(f"Error in fetch_waybills_for_all_cars: {str(e)}")
            return {'success': False, 'error': str(e)}
        finally:
            # Cleanup temporary certificate files once all requests are done
            if hasattr(self.client, 'cleanup'):
                self.client.cleanup()
    
    def get_waybills(self) -> List[BNSFWaybill]:
        """Get all waybills from database"""
        return self.processor.get_all_waybills()
    
    def get_waybill_data(self, waybill_id: int) -> Optional[BNSFWaybill]:
        """Get specific waybill data"""
        return self.processor.get_waybill_data(waybill_id)