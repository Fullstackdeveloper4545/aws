from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.cache import cache
import uuid
import threading
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging
from .models import BNSFWaybill, BNSFCertificate
from .forms import BNSFCertificateForm
from .bnsf_integration import BNSFDataFetcher

logger = logging.getLogger(__name__)

@login_required
def bnsf_fetch_data(request):
    """BNSF API credentials and data fetching view"""
    certificates = BNSFCertificate.objects.filter(is_active=True).order_by('-created_at')
    
    if request.method == 'POST':
        form = BNSFCertificateForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Certificate uploaded successfully.')
            return redirect('core:bnsf_fetch_data')
    else:
        form = BNSFCertificateForm()
    
    context = {
        'form': form,
        'certificates': certificates,
    }
    
    return render(request, 'core/bnsf_fetch_data.html', context)

@login_required
def bnsf_data_list(request):
    """List all BNSF waybill data"""
    waybills = BNSFWaybill.objects.all().order_by('-processed_at')
    
    context = {
        'waybills': waybills,
    }
    
    return render(request, 'core/bnsf_data_list.html', context)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def fetch_bnsf_waybill(request):
    """API endpoint to fetch BNSF waybill data"""
    try:
        logger.info("BNSF waybill fetch request received")
        
        # Parse request data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        
        equipment_initial = data.get('equipment_initial', '').strip()
        equipment_number = data.get('equipment_number', '').strip()
        
        logger.info(f"Fetching waybill for {equipment_initial}{equipment_number}")
        
        if not equipment_initial or not equipment_number:
            logger.warning("Missing equipment initial or number")
            return JsonResponse({
                'success': False,
                'error': 'Equipment initial and number are required'
            }, status=400)
        
        # Get the first active certificate
        try:
            certificate = BNSFCertificate.objects.filter(is_active=True).first()
            if not certificate:
                logger.error("No active BNSF certificate found")
                return JsonResponse({
                    'success': False,
                    'error': 'No active BNSF certificate found. Please upload a certificate first.'
                }, status=400)
            
            logger.info(f"Using certificate: {certificate.name}")
            
        except Exception as e:
            logger.error(f"Error getting certificate: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Error accessing certificate data'
            }, status=500)
        
        # Fetch data
        try:
            fetcher = BNSFDataFetcher(certificate.id)
            result = fetcher.fetch_single_waybill(equipment_initial, equipment_number)
            
            if result['success']:
                logger.info(f"Successfully fetched waybill for {equipment_initial}{equipment_number}")
                return JsonResponse({
                    'success': True,
                    'message': f'Successfully fetched waybill for {equipment_initial}{equipment_number}',
                    'waybill_id': result.get('waybill_id')
                })
            else:
                error_msg = result.get('error', 'Failed to fetch waybill data')
                logger.error(f"Failed to fetch waybill: {error_msg}")
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=400)
                
        except ValueError as e:
            logger.error(f"Certificate error: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Certificate error: {str(e)}'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in BNSFDataFetcher: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Error fetching data: {str(e)}'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Unexpected error in fetch_bnsf_waybill: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred while fetching data'
        }, status=500)

@login_required
def get_waybill_data(request, waybill_id):
    """Get specific waybill data"""
    try:
        waybill = get_object_or_404(BNSFWaybill, id=waybill_id)
        
        return JsonResponse({
            'success': True,
            'data': {
                'waybill_data': waybill.waybill_data,
                'equipment_initial': waybill.equipment_initial,
                'equipment_number': waybill.equipment_number,
                'processed_at': waybill.processed_at.isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error getting waybill data: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while retrieving data'
        }, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def start_bnsf_fetch(request):
    """Start BNSF data fetch process"""
    try:
        logger.info("BNSF bulk fetch request received")
        
        certificate_id = request.POST.get('certificate_id')
        api_url = request.POST.get('api_url', 'https://api-trial.bnsf.com:6443/v1/cars')
        # Use default known waybill endpoint; no need to ask on frontend
        waybill_api_url = 'https://api-trial.bnsf.com:6443/v1/waybill'
        skip_ssl = request.POST.get('skip_ssl', 'false').lower() == 'true'
        
        if not certificate_id:
            logger.warning("No certificate ID provided")
            return JsonResponse({
                'success': False,
                'message': 'Certificate ID is required'
            }, status=400)
        
        # Update certificate with new settings
        try:
            certificate = get_object_or_404(BNSFCertificate, id=certificate_id)
            # Persist provided endpoints
            certificate.api_url = api_url
            certificate.cars_api_url = api_url
            certificate.waybill_api_url = waybill_api_url
            certificate.skip_verify = skip_ssl
            certificate.save()
            logger.info(f"Updated certificate {certificate.name} with new settings")
        except Exception as e:
            logger.error(f"Error updating certificate: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error updating certificate: {str(e)}'
            }, status=500)
        
        # Start fetch process: fetch cars, extract pairs, fetch and save waybills
        try:
            fetcher = BNSFDataFetcher(certificate.id)

            # Create a unique job id for this run
            job_id = f"bnsf_fetch_{certificate.id}_{uuid.uuid4().hex[:8]}"
            cache_key = f"bnsf_progress_{job_id}"
            cache.set(cache_key, {
                'success': True,
                'done': False,
                'total': 0,
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'total_waybills_in_db': 0,
                'message': 'Starting fetch...'
            }, timeout=60*30)

            # Inner helper to push progress
            def update_progress(total=None, processed=None, successful=None, failed=None, message=None):
                state = cache.get(cache_key) or {}
                if total is not None: state['total'] = total
                if processed is not None: state['processed'] = processed
                if successful is not None: state['successful'] = successful
                if failed is not None: state['failed'] = failed
                if message is not None: state['message'] = message
                state['total_waybills_in_db'] = BNSFWaybill.objects.count()
                cache.set(cache_key, state, timeout=60*30)

            # Run the long job in a background thread so the frontend can poll immediately
            def run_job():
                try:
                    # Fetch cars first
                    cars_result = fetcher.fetch_all_cars()
                    if not cars_result.get('success'):
                        update_progress(message=cars_result.get('error', 'Failed to fetch cars'))
                        state = cache.get(cache_key) or {}
                        state.update({'done': True})
                        cache.set(cache_key, state, timeout=60*30)
                        return

                    cars_payload = cars_result.get('data')
                    pairs = fetcher._extract_equipment_pairs(cars_payload)
                    total_pairs = len(pairs)
                    update_progress(total=total_pairs, processed=0, successful=0, failed=0, message=f'Found {total_pairs} cars')

                    # Process waybills sequentially to support frequent progress updates
                    processed = successful = failed = 0
                    for p in pairs:
                        res = fetcher.fetch_single_waybill(p['equipment_initial'], p['equipment_number'])
                        processed += 1
                        if res.get('success'):
                            successful += 1
                        else:
                            failed += 1
                        if processed % 1 == 0:
                            update_progress(total=total_pairs, processed=processed, successful=successful, failed=failed, message='Processing waybills...')

                    state = cache.get(cache_key) or {}
                    state.update({'done': True, 'message': 'Fetch completed'})
                    cache.set(cache_key, state, timeout=60*30)
                except Exception as e:
                    state = cache.get(cache_key) or {}
                    state.update({'done': True, 'message': f'Error: {str(e)}'})
                    cache.set(cache_key, state, timeout=60*30)

            t = threading.Thread(target=run_job, daemon=True)
            t.start()

            # Return immediately with the job id; frontend will poll
            return JsonResponse({
                'success': True,
                'message': 'Fetch started',
                'job_id': job_id,
            })
                
        except ValueError as e:
            logger.error(f"Certificate error in bulk fetch: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Certificate error: {str(e)}'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in bulk fetch: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error during fetch: {str(e)}'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Unexpected error in start_bnsf_fetch: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'An unexpected error occurred while starting the fetch process'
        }, status=500)

@login_required
def get_bnsf_progress(request, job_id):
    """Get BNSF fetch progress"""
    try:
        cache_key = f"bnsf_progress_{job_id}"
        state = cache.get(cache_key)

        if not state:
            # Fallback: show DB count if no cached summary
            return JsonResponse({
                'success': True,
                'done': True,
                'total': 0,
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'total_waybills_in_db': BNSFWaybill.objects.count(),
                'message': 'No recent fetch summary found'
            })
        return JsonResponse({
            'success': True,
            'done': bool(state.get('done', False)),
            'total': state.get('total', 0),
            'processed': state.get('processed', 0),
            'successful': state.get('successful', 0),
            'failed': state.get('failed', 0),
            'total_waybills_in_db': state.get('total_waybills_in_db', BNSFWaybill.objects.count()),
            'message': state.get('message', ''),
        })
    except Exception as e:
        logger.error(f"Error getting BNSF progress: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while checking progress'
        }, status=500)
