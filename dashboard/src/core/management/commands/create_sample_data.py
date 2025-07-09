from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import FileProcess, ApiCall
import uuid
import random
import json
from datetime import timedelta

class Command(BaseCommand):
    help = 'Create sample data for the dashboard'

    def add_arguments(self, parser):
        parser.add_argument(
            '--processes',
            type=int,
            default=10,
            help='Number of file processes to create'
        )
        parser.add_argument(
            '--api-calls-per-process',
            type=int,
            default=20,
            help='Number of API calls per process'
        )

    def handle(self, *args, **options):
        num_processes = options['processes']
        api_calls_per_process = options['api_calls_per_process']
        
        self.stdout.write(f'Creating {num_processes} file processes...')
        
        # Sample filenames
        sample_filenames = [
            'customer_data_2024.csv',
            'sales_report_q1.xlsx',
            'inventory_update.json',
            'user_analytics.csv',
            'financial_data_2024.xlsx',
            'product_catalog.json',
            'order_history.csv',
            'employee_data.xlsx',
            'supplier_info.json',
            'marketing_data.csv'
        ]
        
        # Sample S3 locations
        sample_s3_locations = [
            's3://bucket-name/data/customer_data_2024.csv',
            's3://bucket-name/reports/sales_report_q1.xlsx',
            's3://bucket-name/inventory/inventory_update.json',
            's3://bucket-name/analytics/user_analytics.csv',
            's3://bucket-name/finance/financial_data_2024.xlsx'
        ]
        
        # Sample statuses
        statuses = ['Pending', 'Downloaded', 'Uploaded', 'Queued', 'Processing', 'Processed', 'Failed']
        
        # Create file processes
        for i in range(num_processes):
            process = FileProcess.objects.create(
                filename=random.choice(sample_filenames),
                s3_location=random.choice(sample_s3_locations) if random.random() > 0.3 else None,
                status=random.choice(statuses),
                created_at=timezone.now() - timedelta(
                    days=random.randint(0, 30),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
            )
            
            # Create API calls for this process
            for j in range(api_calls_per_process):
                # Sample JSON payload
                payload = {
                    "row_id": j + 1,
                    "customer_id": f"CUST{random.randint(1000, 9999)}",
                    "name": f"Customer {j + 1}",
                    "email": f"customer{j + 1}@example.com",
                    "amount": round(random.uniform(10.0, 1000.0), 2),
                    "timestamp": timezone.now().isoformat()
                }
                
                # Sample API responses
                success_response = {
                    "status": "success",
                    "message": "Data processed successfully",
                    "processed_at": timezone.now().isoformat(),
                    "row_id": j + 1
                }
                
                error_response = {
                    "status": "error",
                    "message": "Invalid data format",
                    "error_code": "INVALID_FORMAT",
                    "row_id": j + 1
                }
                
                # Determine if this API call should be successful or failed
                is_successful = random.random() > 0.2  # 80% success rate
                
                if is_successful:
                    api_status = random.choice([200, 201, 202])
                    api_response = json.dumps(success_response, indent=2)
                    error_message = None
                else:
                    api_status = random.choice([400, 401, 403, 404, 500])
                    api_response = json.dumps(error_response, indent=2)
                    error_message = random.choice([
                        "Invalid data format",
                        "Authentication failed",
                        "Rate limit exceeded",
                        "Server error",
                        "Network timeout"
                    ])
                
                ApiCall.objects.create(
                    file_process=process,
                    json_payload=payload,
                    api_status=api_status,
                    api_response=api_response,
                    error_message=error_message,
                    created_at=process.created_at + timedelta(
                        minutes=random.randint(1, 60)
                    )
                )
            
            self.stdout.write(f'Created process {i + 1}/{num_processes} with {api_calls_per_process} API calls')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {num_processes} file processes with {num_processes * api_calls_per_process} total API calls'
            )
        )