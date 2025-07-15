# Marium - FTP Data Processing Pipeline with Dashboard

A comprehensive data processing pipeline that monitors FTP servers, processes files through AWS Lambda functions, and provides a web dashboard for monitoring and management with email notifications.

## 🏗️ Architecture Overview

```
FTP Server → EventBridge (1min schedule) → FTP Reader Lambda → SQS → Transformer Lambda → External API → Dashboard
```

### Core Components

1. **FTP Reader Lambda**: Monitors FTP server for new files, parses train data files, and queues JSON data with email notifications
2. **Transformer Lambda**: Processes JSON data from SQS and sends to external APIs
3. **Django Dashboard**: Web interface for monitoring file processing status, API calls, and email configuration
4. **PostgreSQL Database**: Stores file processing metadata, API call history, and email configurations
5. **AWS Infrastructure**: SQS, Lambda, RDS, VPC, and security groups
6. **SendGrid Integration**: Email notifications for processing failures

## 📁 Project Structure

```
middleware/
├── dashboard/                 # Django web dashboard
│   ├── src/
│   │   ├── account/          # User authentication and management
│   │   ├── core/             # File processing models, views, and email config
│   │   └── dashboard/        # Django project settings
│   ├── docker-compose.yml    # Development environment
│   ├── docker-compose-prod.yml # Production environment
│   ├── Dockerfile           # Production container
│   ├── deploy.sh            # Dashboard deployment script
│   └── requirements.txt     # Python dependencies
├── ftp_reader/              # FTP monitoring Lambda
│   ├── lambda_handler.py    # Main Lambda function
│   ├── db_manager.py        # Database operations
│   ├── ftp_manager.py       # FTP server operations
│   ├── train_data_parser.py # Train data parsing logic
│   └── email_manager.py     # SendGrid email notifications
├── transformer/             # Data transformation Lambda
│   ├── lambda_handler.py    # API integration function
│   └── db_manager.py        # Database operations
├── layer/                   # Lambda layer dependencies
│   └── requirements.txt     # Shared Python packages
├── template_infrastructure.yaml # Infrastructure stack (VPC, RDS, SQS)
├── template_application.yaml # Application stack (Lambda functions)
├── deploy.sh               # Main deployment script
└── samconfig.toml          # SAM configuration
```

## 🚀 Quick Start

### Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.9+
- Docker and Docker Compose (for dashboard)
- PostgreSQL (for local development)
- SendGrid account (for email notifications)

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
- Create/update the CloudFormation stacks
- Set up VPC, subnets, security groups
- Deploy Lambda functions with necessary IAM roles
- Create SQS queues and RDS instance
- Configure EventBridge scheduling

### 2. Configure Environment Variables

Update the CloudFormation template parameters or use the deployment script with custom values:

```yaml
Parameters:
  APIEndpoint: "https://your-api-endpoint.com"
  PGPassword: "your-secure-password"
  SendGridApiKey: "your-sendgrid-api-key"
  SendGridFromEmail: "notifications@yourdomain.com"
  SendGridFromName: "FTP Reader System"
```

### 3. Start the Dashboard

```bash
cd dashboard

# Run the dashboard deployment script
chmod +x deploy.sh
./deploy.sh

# Or manually:
# Copy environment file
cp env.example .env

# Edit environment variables
nano .env

# Start with Docker Compose
docker-compose -f docker-compose-prod.yml up -d
```

**Note**: On the server (EC2), the deployed application is located at `/var/www`.

## 🔧 Configuration

### AWS Lambda Functions

#### FTP Reader Lambda
- **Trigger**: EventBridge schedule (every 1 minute)
- **Function**: `ftp_reader/lambda_handler.py`
- **Environment Variables**:
  - `SQS_QUEUE_URL`: SQS queue URL for transformer
  - `PG_HOST`, `PG_PORT`, `PG_DB`, `PG_USER`, `PG_PASSWORD`: Database connection
  - `FTP_HOST`, `FTP_USERNAME`, `FTP_PASSWORD`, `FTP_PORT`: FTP server connection
  - `FTP_SOURCE_FOLDER`, `FTP_DEST_FOLDER`: FTP folder configuration
  - `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`, `SENDGRID_FROM_NAME`: Email notifications

#### Transformer Lambda
- **Trigger**: SQS messages from FTP reader
- **Function**: `transformer/lambda_handler.py`
- **Environment Variables**:
  - `PG_HOST`, `PG_PORT`, `PG_DB`, `PG_USER`, `PG_PASSWORD`: Database connection
  - `API_ENDPOINT`: External API endpoint
  - `API_TIMEOUT`: Request timeout (default: 30s)
  - `API_HEADERS`: Additional headers (JSON format)

### Django Dashboard

#### Database Configuration
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ftp_processor',
        'USER': 'postgres',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',  # or RDS endpoint
        'PORT': '5432',
    }
}
```

#### Email Configuration
- Access email configuration through the dashboard
- Add recipient email addresses for failure notifications
- Configure SendGrid settings in Lambda environment variables

## 📊 Data Models

### FileProcess Model
Tracks file processing status and metadata:

```python
class FileProcess(models.Model):
    unique_id = models.UUIDField(primary_key=True)
    filename = models.CharField(max_length=255)
    location = models.CharField(max_length=500)  # File location (FTP path)
    status = models.CharField(max_length=20)  # Pending, Downloaded, Queued, Processing, Processed, Failed
    site_id = models.CharField(max_length=255, null=True)
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

### EmailConfig Model
Manages email notification recipients:

```python
class EmailConfig(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## 🔄 Data Flow

### 1. File Processing Process
1. EventBridge triggers FTP Reader Lambda every minute
2. Lambda connects to FTP server and checks for new files
3. New files are moved to processed folder and parsed into JSON format
4. JSON data sent to SQS queue
5. Database updated with processing status
6. Email notifications sent for failures

### 2. Data Transformation Process
1. Transformer Lambda receives SQS message
2. JSON data sent to external API endpoint
3. API response and status stored in database
4. File processing status updated

### 3. Dashboard Monitoring
1. Django dashboard queries database
2. Displays file processing status and API call history
3. Provides user authentication and management
4. Manages email configuration for notifications
5. Real-time monitoring of pipeline health

## 🐳 Docker Deployment

### Development Environment
```bash
cd dashboard
docker-compose up -d
```

### Production Environment
```bash
cd dashboard
./deploy.sh  # Automated deployment script
# Or manually:
docker-compose -f docker-compose-prod.yml up -d
```

## 🔍 Monitoring and Logging

### CloudWatch Logs
- **FTP Reader**: `/aws/lambda/ftp-reader`
- **Transformer**: `/aws/lambda/transformer`

### Key Metrics to Monitor
- Lambda execution duration and errors
- SQS queue depth and message processing
- RDS connection pool and query performance
- FTP connection success/failure rates
- API response times and success rates
- Email notification delivery rates

### Dashboard Monitoring
- File processing status overview
- API call success/failure rates
- Error message tracking
- Processing timeline visualization
- Email configuration management

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

# Test FTP Reader
sam local invoke FTPReaderFunction --event events/scheduled-event.json

# Test Transformer
sam local invoke TransformerFunction --event events/sqs-message-event.json
```

## 🔒 Security Considerations

- **IAM Roles**: Least privilege principle for Lambda functions
- **VPC Configuration**: Private subnets for RDS, public subnets for internet access
- **Security Groups**: Restrictive inbound/outbound rules
- **Encryption**: Data encrypted at rest and in transit
- **Secrets Management**: Consider using AWS Secrets Manager for production
- **Email Security**: SendGrid API keys stored securely in environment variables

## 💰 Cost Optimization

- **Lambda**: Optimize timeout and memory settings
- **RDS**: Use appropriate instance size and storage
- **SQS**: Monitor queue depth and adjust processing
- **CloudWatch**: Set up billing alerts
- **EventBridge**: Monitor scheduled rule execution

## 🚨 Troubleshooting

### Common Issues

1. **Lambda Function Errors**
   ```bash
   aws logs tail /aws/lambda/ftp-reader --follow
   aws logs tail /aws/lambda/transformer --follow
   ```

2. **Database Connection Issues**
   - Check RDS security group rules
   - Verify database credentials
   - Test connectivity from Lambda VPC

3. **FTP Connection Issues**
   - Verify FTP server credentials
   - Check network connectivity
   - Review FTP server logs

4. **Email Notification Issues**
   - Verify SendGrid API key
   - Check email configuration in dashboard
   - Review SendGrid delivery logs

5. **SQS Message Processing**
   ```bash
   aws sqs get-queue-attributes --queue-url <queue-url> --attribute-names All
   ```

6. **Dashboard Issues**
   - Check Django logs: `docker-compose logs dashboard`
   - Verify database migrations: `python manage.py showmigrations`
   - Test static files: `python manage.py collectstatic`

### Debugging Commands

```bash
# Check CloudFormation stack status
aws cloudformation describe-stacks --stack-name marium-application

# List Lambda functions
aws lambda list-functions

# Check SQS queue status
aws sqs list-queues

# Test database connectivity
psql -h <rds-endpoint> -U postgres -d ftp_processor

# Check email configurations
python manage.py shell
>>> from core.models import EmailConfig
>>> EmailConfig.objects.all()
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