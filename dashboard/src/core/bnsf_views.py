from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
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
            certificate.api_url = api_url
            certificate.skip_verify = skip_ssl
            certificate.save()
            logger.info(f"Updated certificate {certificate.name} with new settings")
        except Exception as e:
            logger.error(f"Error updating certificate: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error updating certificate: {str(e)}'
            }, status=500)
        
        # Start fetch process
        try:
            fetcher = BNSFDataFetcher(certificate.id)
            result = fetcher.fetch_all_cars()
            
            if result['success']:
                logger.info("Bulk fetch completed successfully")
                return JsonResponse({
                    'success': True,
                    'message': 'Data fetch completed successfully',
                    'job_id': 'bnsf_fetch_' + str(certificate.id),
                    'data': result.get('data', {})
                })
            else:
                error_msg = result.get('error', 'Failed to start data fetch')
                logger.error(f"Bulk fetch failed: {error_msg}")
                return JsonResponse({
                    'success': False,
                    'message': error_msg
                }, status=400)
                
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
        # For now, return mock progress data
        # In a real implementation, this would track actual progress
        return JsonResponse({
            'success': True,
            'done': True,
            'total': 0,
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'total_waybills_in_db': BNSFWaybill.objects.count(),
            'message': 'Fetch completed'
        })
    except Exception as e:
        logger.error(f"Error getting BNSF progress: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while checking progress'
        }, status=500)
