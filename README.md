# Marium - FTP to S3 Data Processing Pipeline with Dashboard

A comprehensive data processing pipeline that monitors FTP servers, processes files through AWS Lambda functions, and provides a web dashboard for monitoring and management.

## 🏗️ Architecture Overview

```
FTP Server → S3 Upload → EventBridge (5min schedule) → FTP Listener Lambda → SQS → Transformer Lambda → External API → Dashboard
```

### Core Components

1. **FTP Listener Lambda**: Monitors S3 for new file uploads, parses train data files, and queues JSON data
2. **Transformer Lambda**: Processes JSON data from SQS and sends to external APIs
3. **Django Dashboard**: Web interface for monitoring file processing status and API calls
4. **PostgreSQL Database**: Stores file processing metadata and API call history
5. **AWS Infrastructure**: S3, SQS, Lambda, RDS, VPC, and security groups

## 📁 Project Structure

```
middleware/
├── dashboard/                 # Django web dashboard
│   ├── src/
│   │   ├── account/          # User authentication
│   │   ├── core/             # File processing models and views
│   │   └── dashboard/        # Django project settings
│   ├── docker-compose.yml    # Development environment
│   ├── Dockerfile           # Production container
│   └── requirements.txt     # Python dependencies
├── ftp_listener/            # FTP monitoring Lambda
│   ├── lambda_handler.py    # Main Lambda function
│   ├── db_manager.py        # Database operations
│   └── train_data_parser.py # Train data parsing logic
├── transformer/             # Data transformation Lambda
│   ├── lambda_handler.py    # API integration function
│   └── db_manager.py        # Database operations
├── layer/                   # Lambda layer dependencies
├── template.yaml            # Main CloudFormation template
├── template_public_rds.yaml # Public RDS template
├── template_private_rds_with_sec_grp.yaml # Private RDS template
├── deploy.sh               # Deployment script
└── samconfig.toml          # SAM configuration
```

## 🚀 Quick Start

### Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.9+
- Docker and Docker Compose (for dashboard)
- PostgreSQL (for local development)

### 1. Deploy AWS Infrastructure

```bash
# Clone the repository
git clone <repository-url>
cd middleware

# Run the deployment script
chmod +x deploy.sh
./deploy.sh
```

The deployment script will:
- Create/update the CloudFormation stack
- Set up VPC, subnets, security groups
- Deploy Lambda functions with necessary IAM roles
- Create S3 bucket, SQS queues, and RDS instance

### 2. Configure Environment Variables

Update the `template.yaml` parameters or use the deployment script with custom values:

```yaml
Parameters:
  S3BucketName: "your-unique-bucket-name"
  APIEndpoint: "https://your-api-endpoint.com"
  PGPassword: "your-secure-password"
  EC2KeyPairName: "your-key-pair"
```

### 3. Start the Dashboard

```bash
cd dashboard

# Copy environment file
cp env.example .env

# Edit environment variables
nano .env

# Start with Docker Compose
docker-compose up -d

# Or run locally
pip install -r requirements.txt
python src/manage.py migrate
python src/manage.py runserver
```

## 🔧 Configuration

### AWS Lambda Functions

#### FTP Listener Lambda
- **Trigger**: S3 upload events via EventBridge
- **Function**: `ftp_listener/lambda_handler.py`
- **Environment Variables**:
  - `S3_BUCKET`: S3 bucket name
  - `SQS_QUEUE_URL`: SQS queue URL for transformer

#### Transformer Lambda
- **Trigger**: SQS messages from FTP listener
- **Function**: `transformer/lambda_handler.py`
- **Environment Variables**:
  - `API_ENDPOINT`: External API endpoint
  - `API_TIMEOUT`: Request timeout (default: 30s)
  - `API_HEADERS`: Additional headers (JSON format)

### Django Dashboard

#### Database Configuration
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'marium_dashboard',
        'USER': 'postgres',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',  # or RDS endpoint
        'PORT': '5432',
    }
}
```

#### AWS S3 Configuration
```python
AWS_ACCESS_KEY_ID = 'your-access-key'
AWS_SECRET_ACCESS_KEY = 'your-secret-key'
AWS_STORAGE_BUCKET_NAME = 'your-bucket-name'
AWS_S3_REGION_NAME = 'us-east-1'
```

## 📊 Data Models

### FileProcess Model
Tracks file processing status and metadata:

```python
class FileProcess(models.Model):
    unique_id = models.UUIDField(primary_key=True)
    site_id = models.CharField(max_length=255)
    filename = models.CharField(max_length=255)
    s3_location = models.CharField(max_length=500)
    status = models.CharField(max_length=20)  # Pending, Downloaded, Queued, Processing, Processed, Failed
    error_message = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### ApiCall Model
Stores API call history and responses:

```python
class ApiCall(models.Model):
    file_process = models.ForeignKey(FileProcess, on_delete=models.CASCADE)
    json_payload = models.JSONField()
    api_status = models.IntegerField()
    api_response = models.TextField(null=True)
    error_message = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

## 🔄 Data Flow

### 1. File Upload Process
1. File uploaded to S3 bucket
2. EventBridge triggers FTP Listener Lambda
3. Lambda parses train data file into JSON format
4. JSON data sent to SQS queue
5. Database updated with processing status

### 2. Data Transformation Process
1. Transformer Lambda receives SQS message
2. JSON data sent to external API endpoint
3. API response and status stored in database
4. File processing status updated

### 3. Dashboard Monitoring
1. Django dashboard queries database
2. Displays file processing status and API call history
3. Provides user authentication and management
4. Real-time monitoring of pipeline health

## 🐳 Docker Deployment

### Development Environment
```bash
cd dashboard
docker-compose up -d
```

### Production Environment
```bash
cd dashboard
docker-compose -f docker-compose-prod.yml up -d
```

## 🔍 Monitoring and Logging

### CloudWatch Logs
- **FTP Listener**: `/aws/lambda/ftp-listener`
- **Transformer**: `/aws/lambda/transformer`

### Key Metrics to Monitor
- Lambda execution duration and errors
- SQS queue depth and message processing
- RDS connection pool and query performance
- S3 bucket storage and access patterns
- API response times and success rates

### Dashboard Monitoring
- File processing status overview
- API call success/failure rates
- Error message tracking
- Processing timeline visualization

## 🛠️ Development

### Local Development Setup

1. **Set up Python environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r dashboard/requirements.txt
```

2. **Configure local database**:
```bash
# Install PostgreSQL locally or use Docker
docker run --name postgres -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres
```

3. **Run Django development server**:
```bash
cd dashboard/src
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Testing Lambda Functions Locally

```bash
# Install SAM CLI
pip install aws-sam-cli

# Test FTP Listener
sam local invoke FTPListenerFunction --event events/s3-upload-event.json

# Test Transformer
sam local invoke TransformerFunction --event events/sqs-message-event.json
```

## 🔒 Security Considerations

- **IAM Roles**: Least privilege principle for Lambda functions
- **VPC Configuration**: Private subnets for RDS, public subnets for internet access
- **Security Groups**: Restrictive inbound/outbound rules
- **Encryption**: Data encrypted at rest and in transit
- **Secrets Management**: Consider using AWS Secrets Manager for production

## 💰 Cost Optimization

- **Lambda**: Optimize timeout and memory settings
- **RDS**: Use appropriate instance size and storage
- **S3**: Implement lifecycle policies for old files
- **SQS**: Monitor queue depth and adjust processing
- **CloudWatch**: Set up billing alerts

## 🚨 Troubleshooting

### Common Issues

1. **Lambda Function Errors**
   ```bash
   aws logs tail /aws/lambda/ftp-listener --follow
   aws logs tail /aws/lambda/transformer --follow
   ```

2. **Database Connection Issues**
   - Check RDS security group rules
   - Verify database credentials
   - Test connectivity from Lambda VPC

3. **SQS Message Processing**
   ```bash
   aws sqs get-queue-attributes --queue-url <queue-url> --attribute-names All
   ```

4. **Dashboard Issues**
   - Check Django logs: `docker-compose logs dashboard`
   - Verify database migrations: `python manage.py showmigrations`
   - Test static files: `python manage.py collectstatic`

### Debugging Commands

```bash
# Check CloudFormation stack status
aws cloudformation describe-stacks --stack-name ftp-transformer

# List Lambda functions
aws lambda list-functions

# Check SQS queue status
aws sqs list-queues

# Test database connectivity
psql -h <rds-endpoint> -U postgres -d marium_dashboard
```

## 📈 Scaling Considerations

- **Horizontal Scaling**: Multiple Lambda instances for high throughput
- **Database Scaling**: RDS read replicas for dashboard queries
- **Caching**: Redis for session storage and API response caching
- **CDN**: CloudFront for static assets
- **Auto Scaling**: Application Load Balancer for dashboard

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues or questions:
1. Check CloudWatch logs for detailed error information
2. Review AWS CloudFormation stack events
3. Consult the troubleshooting section above
4. Create an issue in the repository with detailed logs and error messages 