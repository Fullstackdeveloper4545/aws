# FTP to S3 Lambda Handler with Transformer

This project implements an automated FTP to S3 file processing system using AWS Lambda functions, SQS, and DynamoDB. The system monitors an FTP server every 5 minutes, downloads CSV files, uploads them to S3, and triggers a transformer lambda to process the files.

## Architecture

```
FTP Server → EventBridge (5min schedule) → FTP Listener Lambda → S3 → SQS → Transformer Lambda → Transformed Files in S3
```

### Components

1. **EventBridge Rule**: Triggers the FTP Listener Lambda every 5 minutes
2. **FTP Listener Lambda**: Connects to FTP server, downloads CSV files, uploads to S3, and sends SQS messages
3. **S3 Bucket**: Stores original and transformed files
4. **SQS Queue**: Triggers the Transformer Lambda when new files are uploaded
5. **Transformer Lambda**: Processes files from S3 and creates transformed versions
6. **DynamoDB Table**: Tracks file processing status and metadata

## Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.9+
- AWS SAM CLI (optional, for local testing)

## Deployment

### 1. Update Parameters

Edit the `template.yaml` file to customize the following parameters:

```yaml
Parameters:
  FTPHost: "your-ftp-server.com"
  FTPUsername: "your-username"
  FTPPassword: "your-password"
  FTPDirectory: "/path/to/files"
  S3BucketName: "your-unique-bucket-name"
  DynamoDBTableName: "ftp-file-processing"
  SQSQueueName: "ftp-processing-queue"
  FTPListenerFunctionName: "ftp-listener"
  TransformerFunctionName: "transformer"
  ScheduleExpression: "rate(5 minutes)"
```

### 2. Deploy the Stack

```bash
# Deploy using AWS CLI
aws cloudformation create-stack \
  --stack-name ftp-s3-transformer \
  --template-body file://template.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=FTPHost,ParameterValue=your-ftp-server.com \
    ParameterKey=FTPUsername,ParameterValue=your-username \
    ParameterKey=FTPPassword,ParameterValue=your-password

# Or update existing stack
aws cloudformation update-stack \
  --stack-name ftp-s3-transformer \
  --template-body file://template.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=FTPHost,ParameterValue=your-ftp-server.com \
    ParameterKey=FTPUsername,ParameterValue=your-username \
    ParameterKey=FTPPassword,ParameterValue=your-password
```

### 3. Monitor Deployment

```bash
aws cloudformation describe-stacks --stack-name ftp-s3-transformer
```

## How It Works

### 1. FTP Listener Lambda (Every 5 minutes)

1. Connects to the configured FTP server
2. Lists CSV files in the specified directory
3. For each CSV file:
   - Downloads the file from FTP
   - Uploads it to S3 with a unique key
   - Creates a DynamoDB record to track processing
   - Sends an SQS message with file details
   - Updates the DynamoDB status

### 2. Transformer Lambda (Triggered by SQS)

1. Receives SQS messages with file details
2. Downloads the original file from S3
3. Applies transformations:
   - For CSV files: Adds a `transformed_at` column with timestamps
   - For other files: Adds a transformation header
4. Uploads the transformed file to S3 in a `transformed/` subdirectory
5. Includes metadata about the transformation

## File Structure

```
ftp_listener/
├── lambda_handler.py    # FTP Listener Lambda code
└── requirements.txt     # Python dependencies

transformer/
├── lambda_handler.py    # Transformer Lambda code
└── requirements.txt     # Python dependencies

template.yaml            # CloudFormation template
README.md               # This file
```

## S3 File Organization

```
s3://your-bucket/
├── ftp-files/
│   └── 2024/01/15/
│       ├── uuid1_filename1.csv
│       └── uuid2_filename2.csv
└── ftp-files/
    └── 2024/01/15/
        └── transformed/
            ├── uuid1_filename1_transformed.csv
            └── uuid2_filename2_transformed.csv
```

## DynamoDB Schema

```json
{
  "unique_id": "uuid-string",
  "filename": "original-filename.csv",
  "s3_location": "s3://bucket/path/to/file.csv",
  "status": "Pending|Downloaded|Processed|Failed",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

## SQS Message Format

```json
{
  "bucket_name": "your-bucket-name",
  "key": "ftp-files/2024/01/15/uuid_filename.csv",
  "unique_id": "uuid-string",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Monitoring and Logging

### CloudWatch Logs

- **FTP Listener**: `/aws/lambda/ftp-listener`
- **Transformer**: `/aws/lambda/transformer`

### Key Metrics to Monitor

- Lambda execution duration and errors
- SQS queue depth and message processing
- DynamoDB read/write capacity
- S3 bucket storage and access patterns

## Customization

### Modifying Transformations

Edit the `transformer/lambda_handler.py` file to customize file transformations:

```python
def transform_csv_content(content: str) -> str:
    # Add your custom CSV transformation logic here
    lines = content.split('\n')
    transformed_lines = []
    
    for i, line in enumerate(lines):
        if i == 0:
            # Customize header transformation
            transformed_lines.append(f"{line},custom_column")
        else:
            if line.strip():
                # Customize data row transformation
                transformed_lines.append(f"{line},custom_value")
    
    return '\n'.join(transformed_lines)
```

### Changing Schedule

Update the `ScheduleExpression` parameter in `template.yaml`:

```yaml
ScheduleExpression: "rate(1 hour)"  # Every hour
ScheduleExpression: "cron(0 */2 * * ? *)"  # Every 2 hours
ScheduleExpression: "cron(0 9 * * ? *)"  # Daily at 9 AM
```

## Troubleshooting

### Common Issues

1. **FTP Connection Failed**
   - Check FTP server credentials and connectivity
   - Verify firewall settings
   - Check Lambda timeout settings

2. **S3 Upload Failed**
   - Verify IAM permissions
   - Check S3 bucket name and region
   - Ensure bucket exists and is accessible

3. **SQS Message Processing Failed**
   - Check SQS queue permissions
   - Verify message format
   - Monitor CloudWatch logs for errors

### Debugging

```bash
# Check Lambda logs
aws logs tail /aws/lambda/ftp-listener --follow
aws logs tail /aws/lambda/transformer --follow

# Check SQS queue status
aws sqs get-queue-attributes --queue-url https://sqs.region.amazonaws.com/account/queue-name --attribute-names All

# Check DynamoDB items
aws dynamodb scan --table-name ftp-file-processing --limit 10
```

## Security Considerations

- FTP credentials are stored as Lambda environment variables (consider using AWS Secrets Manager for production)
- S3 bucket has public access blocked
- IAM roles follow least privilege principle
- All data is encrypted at rest and in transit

## Cost Optimization

- DynamoDB uses on-demand billing (PAY_PER_REQUEST)
- S3 lifecycle policy deletes files after 365 days
- Lambda timeout set to 5 minutes (300 seconds)
- Consider adjusting schedule frequency based on needs

## Support

For issues or questions, check the CloudWatch logs and AWS CloudFormation stack events for detailed error information. 