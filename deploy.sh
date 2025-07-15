#!/bin/bash

# =============================================================================
# AWS Multi-Stack Deployment Management Script
# =============================================================================

# Configuration
INFRASTRUCTURE_STACK_NAME="marium-infrastructure"
APPLICATION_STACK_NAME="marium-application"
PROFILE="marium"
REGION="us-east-1"
KEY_NAME="marium-key"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Utility Functions
# =============================================================================

# Print colored output
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if AWS CLI is available
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed or not in PATH"
        exit 1
    fi
}

# Check if SAM CLI is available
check_sam_cli() {
    if ! command -v sam &> /dev/null; then
        print_error "AWS SAM CLI is not installed or not in PATH"
        exit 1
    fi
}

# Validate CloudFormation template
validate_template() {
    local template_file="$1"
    print_info "Validating CloudFormation template: $template_file"
    
    if sam validate --template-file "$template_file" --profile "$PROFILE" --region "$REGION"; then
        print_success "Basic SAM validation passed"
        
        print_info "Running additional lint validation..."
        if sam validate --lint --template-file "$template_file" --profile "$PROFILE" --region "$REGION"; then
            print_success "Lint validation passed"
            return 0
        else
            print_warning "Lint validation found issues (non-critical)"
            return 0  # Continue with deployment even if lint has warnings
        fi
    else
        print_error "Template validation failed"
        return 1
    fi
}

# Validate template using AWS CLI
validate_template_aws_cli() {
    local template_file="$1"
    print_info "Validating template using AWS CLI: $template_file"
    
    if aws cloudformation validate-template \
        --template-body file://"$template_file" \
        --profile "$PROFILE" \
        --region "$REGION" >/dev/null 2>&1; then
        print_success "AWS CLI template validation passed"
        return 0
    else
        print_error "AWS CLI template validation failed"
        return 1
    fi
}

# Get stack status
get_stack_status() {
    local stack_name="$1"
    aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --profile "$PROFILE" \
        --region "$REGION" \
        --query 'Stacks[0].StackStatus' \
        --output text 2>/dev/null
}

# Check if stack exists and is in a stable state
is_stack_stable() {
    local stack_name="$1"
    local status
    status=$(get_stack_status "$stack_name")
    
    if [ $? -eq 0 ]; then
        case "$status" in
            "CREATE_COMPLETE"|"UPDATE_COMPLETE"|"UPDATE_ROLLBACK_COMPLETE")
                return 0
                ;;
            *)
                return 1
                ;;
        esac
    else
        return 1
    fi
}

# Get stack output value
get_stack_output() {
    local stack_name="$1"
    local output_key="$2"
    aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --profile "$PROFILE" \
        --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='$output_key'].OutputValue" \
        --output text 2>/dev/null
}

# =============================================================================
# Key Pair Management
# =============================================================================

manage_key_pair() {
    print_info "Checking if key pair '$KEY_NAME' exists..."
    
    local key_exists
    key_exists=$(aws ec2 describe-key-pairs \
        --key-names "$KEY_NAME" \
        --profile "$PROFILE" \
        --region "$REGION" \
        --query 'KeyPairs[0].KeyName' \
        --output text 2>/dev/null)
    
    if [ $? -eq 0 ] && [ "$key_exists" == "$KEY_NAME" ]; then
        print_success "Key pair '$KEY_NAME' already exists."
        return 0
    else
        print_info "Key pair '$KEY_NAME' does not exist. Creating..."
        
        if aws ec2 create-key-pair \
            --key-name "$KEY_NAME" \
            --query 'KeyMaterial' \
            --output text \
            --profile "$PROFILE" \
            --region "$REGION" > "$KEY_NAME.pem" 2>/dev/null; then
            
            chmod 400 "$KEY_NAME.pem"
            print_success "Key pair '$KEY_NAME' created and saved to '$KEY_NAME.pem'"
            print_success "Set proper permissions (400) on '$KEY_NAME.pem'"
            return 0
        else
            print_error "Failed to create key pair '$KEY_NAME'"
            return 1
        fi
    fi
}

# =============================================================================
# Stack Management
# =============================================================================

confirm_action() {
    local message="$1"
    local default="${2:-N}"
    local prompt="Do you want to $message? (y/$default): "
    
    read -p "$prompt" -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

delete_stack() {
    local stack_name="$1"
    local status
    status=$(get_stack_status "$stack_name")
    
    if [ $? -eq 0 ]; then
        print_info "Stack exists with status: $status"
        
        if is_stack_stable "$stack_name"; then
            print_success "Stack '$stack_name' is in a stable state. Skipping deletion."
            return 0
        else
            print_warning "Stack is not in a successful state."
            print_info "Current stack status: $status"
            
            if confirm_action "delete stack '$stack_name'"; then
                print_info "Deleting stack: $stack_name"
                
                if aws cloudformation delete-stack \
                    --stack-name "$stack_name" \
                    --profile "$PROFILE" \
                    --region "$REGION"; then
                    
                    print_info "Waiting for stack to be deleted..."
                    aws cloudformation wait stack-delete-complete \
                        --stack-name "$stack_name" \
                        --profile "$PROFILE" \
                        --region "$REGION"
                    
                    if [ $? -eq 0 ]; then
                        print_success "Stack '$stack_name' has been successfully deleted."
                        return 0
                    else
                        print_error "Stack deletion failed or timed out."
                        return 1
                    fi
                else
                    print_error "Failed to initiate stack deletion."
                    return 1
                fi
            else
                print_info "Stack deletion cancelled."
                return 0
            fi
        fi
    else
        print_info "Stack '$stack_name' does not exist. Proceeding with deployment."
        return 0
    fi
}

# =============================================================================
# Infrastructure Stack Deployment
# =============================================================================

deploy_infrastructure_stack() {
    print_info "Starting infrastructure stack deployment..."
    
    # Check prerequisites
    check_aws_cli
    check_sam_cli
    
    # Validate infrastructure template
    print_info "Validating infrastructure template..."
    if ! validate_template "template_infrastructure.yaml"; then
        print_error "Infrastructure template validation failed."
        return 1
    fi
    
    if ! validate_template_aws_cli "template_infrastructure.yaml"; then
        print_error "Infrastructure template AWS CLI validation failed."
        return 1
    fi
    
    print_success "Infrastructure template validation passed!"
    
    # Manage key pair
    if ! manage_key_pair; then
        return 1
    fi
    
    # Handle existing infrastructure stack
    if ! delete_stack "$INFRASTRUCTURE_STACK_NAME"; then
        return 1
    fi
    
    # Deploy infrastructure stack
    print_info "Deploying infrastructure stack: $INFRASTRUCTURE_STACK_NAME"
    
    if ! sam build --template-file template_infrastructure.yaml --profile "$PROFILE"; then
        print_error "SAM build failed for infrastructure stack"
        return 1
    fi
    
    # Deploy infrastructure stack with real-time output
    print_info "Deploying infrastructure stack..."
    
    if sam deploy --template-file template_infrastructure.yaml \
        --stack-name "$INFRASTRUCTURE_STACK_NAME" \
        --profile "$PROFILE" \
        --capabilities CAPABILITY_NAMED_IAM \
        --no-confirm-changeset; then
        print_success "Infrastructure stack deployment completed successfully"
    else
        local deploy_exit_code=$?
        if [ $deploy_exit_code -eq 0 ]; then
            print_success "Infrastructure stack deployment completed successfully"
        else
            print_error "SAM deploy failed for infrastructure stack"
            return 1
        fi
    fi
    
    # Wait for deployment
    print_info "Waiting for infrastructure stack deployment to complete..."
    if aws cloudformation wait stack-create-complete \
        --stack-name "$INFRASTRUCTURE_STACK_NAME" \
        --profile "$PROFILE" \
        --region "$REGION" 2>/dev/null || \
       aws cloudformation wait stack-update-complete \
        --stack-name "$INFRASTRUCTURE_STACK_NAME" \
        --profile "$PROFILE" \
        --region "$REGION"; then
        
        print_success "Infrastructure stack deployment completed successfully!"
        show_infrastructure_summary
    return 0
    else
        print_error "Infrastructure stack deployment failed!"
        return 1
    fi
}

# =============================================================================
# Application Stack Deployment
# =============================================================================

deploy_application_stack() {
    print_info "Starting application stack deployment..."
    
    # Check if infrastructure stack exists and is stable
    if ! is_stack_stable "$INFRASTRUCTURE_STACK_NAME"; then
        print_error "Infrastructure stack '$INFRASTRUCTURE_STACK_NAME' does not exist or is not stable."
        print_info "Please deploy the infrastructure stack first."
        return 1
    fi
    
    # Check prerequisites
    check_aws_cli
    check_sam_cli
    
    # Validate application template
    print_info "Validating application template..."
    if ! validate_template "template_application.yaml"; then
        print_error "Application template validation failed."
        return 1
    fi
    
    if ! validate_template_aws_cli "template_application.yaml"; then
        print_error "Application template AWS CLI validation failed."
        return 1
    fi
    
    print_success "Application template validation passed!"
    
    # Handle existing application stack
    if ! delete_stack "$APPLICATION_STACK_NAME"; then
        return 1
    fi
    
    # Deploy application stack
    print_info "Deploying application stack: $APPLICATION_STACK_NAME"
    
    if ! sam build --template-file template_application.yaml --profile "$PROFILE"; then
        print_error "SAM build failed for application stack"
        return 1
    fi
    
    # Deploy application stack with real-time output
    print_info "Deploying application stack..."
    
    if sam deploy --template-file template_application.yaml \
        --stack-name "$APPLICATION_STACK_NAME" \
        --profile "$PROFILE" \
        --capabilities CAPABILITY_NAMED_IAM \
        --no-confirm-changeset \
        --parameter-overrides \
        InfrastructureStackName="$INFRASTRUCTURE_STACK_NAME" \
        S3BucketName="ftp-files-bucket-9824"; then
        print_success "Application stack deployment completed successfully"
    else
        local deploy_exit_code=$?
        if [ $deploy_exit_code -eq 0 ]; then
            print_success "Application stack deployment completed successfully"
        else
            print_error "SAM deploy failed for application stack"
        return 1
        fi
    fi
    
    # Wait for deployment
    print_info "Waiting for application stack deployment to complete..."
    if aws cloudformation wait stack-create-complete \
        --stack-name "$APPLICATION_STACK_NAME" \
        --profile "$PROFILE" \
        --region "$REGION" 2>/dev/null || \
       aws cloudformation wait stack-update-complete \
        --stack-name "$APPLICATION_STACK_NAME" \
        --profile "$PROFILE" \
        --region "$REGION"; then
        
        print_success "Application stack deployment completed successfully!"
        show_application_summary
        return 0
    else
        print_error "Application stack deployment failed!"
        return 1
    fi
}

# =============================================================================
# Full Stack Deployment
# =============================================================================

deploy_full_stack() {
    print_info "Starting full stack deployment (infrastructure + application)..."
    
    # Deploy infrastructure first
    if ! deploy_infrastructure_stack; then
        print_error "Infrastructure stack deployment failed. Cannot proceed with application stack."
        return 1
    fi
    
    # Wait a moment for infrastructure to be fully available
    print_info "Waiting for infrastructure to be fully available..."
    sleep 30
    
    # Deploy application stack
    if ! deploy_application_stack; then
        print_error "Application stack deployment failed."
        return 1
    fi
    
    print_success "Full stack deployment completed successfully!"
    show_full_deployment_summary
    return 0
}

# =============================================================================
# Summary Functions
# =============================================================================

show_infrastructure_summary() {
    print_info "Getting infrastructure deployment summary..."
    
    local rds_endpoint
    local ec2_elastic_ip
    local s3_bucket_name
    
    rds_endpoint=$(get_stack_output "$INFRASTRUCTURE_STACK_NAME" "RDSInstanceEndpoint")
    ec2_elastic_ip=$(get_stack_output "$INFRASTRUCTURE_STACK_NAME" "EC2ElasticIP")
    s3_bucket_name=$(get_stack_output "$INFRASTRUCTURE_STACK_NAME" "S3BucketName")
    
    echo ""
    print_success "Infrastructure stack is ready!"
    echo "📋 Infrastructure Details:"
    echo "   RDS Endpoint: $rds_endpoint"
    echo "   EC2 Elastic IP: $ec2_elastic_ip"
    echo "   S3 Bucket: $s3_bucket_name"
    echo ""
    echo "🔗 Next Steps:"
    echo "   - Deploy application stack to add Lambda functions"
    echo "   - Use option 3 to deploy application stack"
}

show_application_summary() {
    print_info "Getting application deployment summary..."
    
    local source_function_arn
    local transformer_function_arn
    
    source_function_arn=$(get_stack_output "$APPLICATION_STACK_NAME" "SourceFunctionArn")
    transformer_function_arn=$(get_stack_output "$APPLICATION_STACK_NAME" "TransformerFunctionArn")
    
    echo ""
    print_success "Application stack is ready!"
    echo "📋 Application Details:"
    echo "   FTP Listener Lambda: $source_function_arn"
    echo "   Transformer Lambda: $transformer_function_arn"
    echo ""
    echo "🔗 Lambda Functions:"
    echo "   - FTP Listener: Processes FTP events and triggers SQS"
    echo "   - Transformer: Processes SQS messages and transforms data"
    echo ""
    echo "🔗 SQS Queues:"
    echo "   - Source Queue: Receives FTP listener notifications"
    echo "   - Processing Queue: Handles data transformation"
    echo ""
    echo "📝 Note: The Lambda functions are now deployed and ready to process data."
}

show_full_deployment_summary() {
    print_info "Getting full deployment summary..."
    
    local rds_endpoint
    local ec2_elastic_ip
    local s3_bucket_name
    local source_function_arn
    local transformer_function_arn
    
    rds_endpoint=$(get_stack_output "$INFRASTRUCTURE_STACK_NAME" "RDSInstanceEndpoint")
    ec2_elastic_ip=$(get_stack_output "$INFRASTRUCTURE_STACK_NAME" "EC2ElasticIP")
    s3_bucket_name=$(get_stack_output "$INFRASTRUCTURE_STACK_NAME" "S3BucketName")
    source_function_arn=$(get_stack_output "$APPLICATION_STACK_NAME" "SourceFunctionArn")
    transformer_function_arn=$(get_stack_output "$APPLICATION_STACK_NAME" "TransformerFunctionArn")
    
    echo ""
    print_success "Full deployment completed successfully!"
    echo "📋 Complete System Details:"
    echo "   Infrastructure Stack: $INFRASTRUCTURE_STACK_NAME"
    echo "   Application Stack: $APPLICATION_STACK_NAME"
    echo ""
    echo "🔗 Infrastructure Components:"
    echo "   RDS Endpoint: $rds_endpoint"
    echo "   EC2 Elastic IP: $ec2_elastic_ip"
    echo "   S3 Bucket: $s3_bucket_name"
    echo ""
    echo "🔗 Application Components:"
    echo "   FTP Listener Lambda: $source_function_arn"
    echo "   Transformer Lambda: $transformer_function_arn"
    echo ""
    echo "🔗 Connection Details:"
    echo "   SSH: ssh -i $KEY_NAME.pem ubuntu@$ec2_elastic_ip"
    echo "   RDS: $rds_endpoint:5432"
    echo ""
    echo "📝 Note: The Lambda functions are now deployed and ready to process data."
}

# =============================================================================
# Template Validation
# =============================================================================

validate_templates() {
    print_info "Validating both templates..."
    
    # Validate infrastructure template
    print_info "Validating infrastructure template..."
    if ! validate_template "template_infrastructure.yaml"; then
        print_error "Infrastructure template validation failed"
        return 1
    fi
    
    # Validate application template
    print_info "Validating application template..."
    if ! validate_template "template_application.yaml"; then
        print_error "Application template validation failed"
        return 1
    fi
    
    print_success "✅ All template validations completed!"
    print_info "Templates are ready for deployment."
    return 0
}

# =============================================================================
# Database User Management
# =============================================================================

show_database_users() {
    print_info "Getting database users..."
    
    if ! is_stack_stable "$INFRASTRUCTURE_STACK_NAME"; then
        print_error "Infrastructure stack does not exist or is not stable"
        return 1
    fi
    
    local rds_endpoint
    rds_endpoint=$(get_stack_output "$INFRASTRUCTURE_STACK_NAME" "RDSInstanceEndpoint")
    
    if [ -z "$rds_endpoint" ]; then
        print_error "Could not retrieve RDS endpoint"
        return 1
    fi
    
    print_info "RDS Endpoint: $rds_endpoint"
    echo ""
    
    # Check if psql is available
    if ! command -v psql &> /dev/null; then
        print_error "psql is not installed or not in PATH"
        print_info "Please install PostgreSQL client tools"
        return 1
    fi
    
    # Try to connect and query users
    print_info "Querying database users..."
    echo ""
    
    if PGPASSWORD="sdlkj67hjvfWE0167VBggF" psql -h "$rds_endpoint" -U postgres -d ftp_processor -c "SELECT username, password_hash, home_directory, is_active FROM ftp_users ORDER BY username;" 2>/dev/null; then
        print_success "Database users retrieved successfully"
        echo ""
        print_info "To add a new user, run:"
        echo "   INSERT INTO ftp_users (username, password_hash, home_directory, role_arn) VALUES"
        echo "   ('newuser', 'password123', '/newuser', 'arn:aws:iam::aws:policy/AWSTransferConsoleFullAccess');"
    else
        print_error "Failed to query database users"
        print_info "This might be because:"
        echo "   1. Database is not accessible from this machine"
        echo "   2. Security groups are blocking access"
        echo "   3. Database credentials are incorrect"
        echo ""
        print_info "You can connect manually using:"
        echo "   PGPASSWORD='sdlkj67hjvfWE0167VBggF' psql -h $rds_endpoint -U postgres -d ftp_processor"
    fi
}

# =============================================================================
# Information Display Functions
# =============================================================================

display_stack_status() {
    local stack_name="$1"
    print_info "Getting stack status for: $stack_name"
    
    local status
    status=$(get_stack_status "$stack_name")
    
    if [ $? -eq 0 ]; then
        print_success "Stack Status: $status"
        
        # Get stack creation/update time
        local stack_time
        stack_time=$(aws cloudformation describe-stacks \
            --stack-name "$stack_name" \
            --profile "$PROFILE" \
            --region "$REGION" \
            --query 'Stacks[0].LastUpdatedTime' \
            --output text 2>/dev/null)
        
        if [ "$stack_time" != "None" ] && [ -n "$stack_time" ]; then
            echo "📅 Last Updated: $stack_time"
        fi
    else
        print_error "Stack '$stack_name' does not exist"
    fi
}

display_all_stack_status() {
    print_info "Getting status for all stacks..."
    echo ""
    echo "=== Infrastructure Stack ==="
    display_stack_status "$INFRASTRUCTURE_STACK_NAME"
    echo ""
    echo "=== Application Stack ==="
    display_stack_status "$APPLICATION_STACK_NAME"
}

display_lambda_details() {
    print_info "Getting Lambda function details..."
    
    if ! is_stack_stable "$APPLICATION_STACK_NAME"; then
        print_error "Application stack does not exist or is not stable"
        return 1
    fi
    
    local source_function_arn
    local transformer_function_arn
    
    source_function_arn=$(get_stack_output "$APPLICATION_STACK_NAME" "SourceFunctionArn")
    transformer_function_arn=$(get_stack_output "$APPLICATION_STACK_NAME" "TransformerFunctionArn")
    
    print_success "Lambda Function Details:"
    echo "   FTP Listener Lambda: $source_function_arn"
    echo "   Transformer Lambda: $transformer_function_arn"
    echo ""
    echo "🔗 Function Purposes:"
    echo "   - FTP Listener: Monitors S3 for new files and triggers SQS"
    echo "   - Transformer: Processes SQS messages and transforms data"
    echo ""
    echo "🔗 AWS CLI Commands:"
    echo "   List functions: aws lambda list-functions --profile $PROFILE"
    echo "   Get function details: aws lambda get-function --function-name ftp-listener --profile $PROFILE"
    echo "   Invoke function: aws lambda invoke --function-name ftp-listener --profile $PROFILE"
}

display_rds_details() {
    print_info "Getting RDS details..."
    
    if ! is_stack_stable "$INFRASTRUCTURE_STACK_NAME"; then
        print_error "Infrastructure stack does not exist or is not stable"
        return 1
    fi
    
    local rds_endpoint
    local rds_port
    
    rds_endpoint=$(get_stack_output "$INFRASTRUCTURE_STACK_NAME" "RDSInstanceEndpoint")
    rds_port=$(get_stack_output "$INFRASTRUCTURE_STACK_NAME" "RDSInstancePort")
    
    print_success "RDS Database Details:"
    echo "   Endpoint: $rds_endpoint"
    echo "   Port: $rds_port"
    echo "   Database Name: ftp_processor"
    echo "   Username: postgres"
    echo "   Password: sdlkj67hjvfWE0167VBggF"
    echo ""
    echo "🔗 Connection Details:"
    echo "   Host: $rds_endpoint"
    echo "   Port: $rds_port"
    echo "   Database: ftp_processor"
    echo "   Username: postgres"
    echo "   Password: sdlkj67hjvfWE0167VBggF"
}

display_ec2_details() {
    print_info "Getting EC2 details..."
    
    if ! is_stack_stable "$INFRASTRUCTURE_STACK_NAME"; then
        print_error "Infrastructure stack does not exist or is not stable"
        return 1
    fi
    
    local ec2_elastic_ip
    
    ec2_elastic_ip=$(get_stack_output "$INFRASTRUCTURE_STACK_NAME" "EC2ElasticIP")
    
    print_success "EC2 Instance Details:"
    echo "   Elastic IP: $ec2_elastic_ip"
    echo "   Key Pair: $KEY_NAME"
    echo ""
    echo "🔗 SSH Connection:"
    echo "   ssh -i $KEY_NAME.pem ubuntu@$ec2_elastic_ip"
}

display_s3_details() {
    print_info "Getting S3 details..."
    
    if ! is_stack_stable "$INFRASTRUCTURE_STACK_NAME"; then
        print_error "Infrastructure stack does not exist or is not stable"
        return 1
    fi
    
    local s3_bucket_name
    s3_bucket_name=$(get_stack_output "$INFRASTRUCTURE_STACK_NAME" "S3BucketName")
    
    print_success "S3 Bucket Details:"
    echo "   Bucket Name: $s3_bucket_name"
    echo "   Region: $REGION"
    echo ""
    echo "🔗 AWS CLI Commands:"
    echo "   List files: aws s3 ls s3://$s3_bucket_name --profile $PROFILE"
    echo "   Upload file: aws s3 cp <file> s3://$s3_bucket_name/ --profile $PROFILE"
    echo "   Download file: aws s3 cp s3://$s3_bucket_name/<file> . --profile $PROFILE"
}

display_sqs_details() {
    print_info "Getting SQS details..."
    
    if ! is_stack_stable "$INFRASTRUCTURE_STACK_NAME"; then
        print_error "Infrastructure stack does not exist or is not stable"
        return 1
    fi
    
    local source_queue_url
    local processing_queue_url
    
    source_queue_url=$(get_stack_output "$APPLICATION_STACK_NAME" "SourceQueueUrl")
    processing_queue_url=$(get_stack_output "$APPLICATION_STACK_NAME" "SQSQueueUrl")
    
    print_success "SQS Queue Details:"
    echo "   Source Queue URL: $source_queue_url"
    echo "   Processing Queue URL: $processing_queue_url"
    echo ""
    echo "🔗 Queue Purposes:"
    echo "   - Source Queue: Receives notifications from FTP listener"
    echo "   - Processing Queue: Handles data transformation tasks"
    echo ""
    echo "🔗 AWS CLI Commands:"
    echo "   List queues: aws sqs list-queues --profile $PROFILE"
    echo "   Get queue attributes: aws sqs get-queue-attributes --queue-url $source_queue_url --profile $PROFILE"
    echo "   Send message: aws sqs send-message --queue-url $source_queue_url --message-body 'test' --profile $PROFILE"
}

# =============================================================================
# Menu System
# =============================================================================

show_menu() {
    echo ""
    echo "=== AWS Multi-Stack Deployment Management ==="
    echo "1. Deploy Full Stack (Infrastructure + Application)"
    echo "2. Deploy Infrastructure Stack Only"
    echo "3. Deploy Application Stack Only"
    echo "4. Validate Templates"
    echo "5. Get All Stack Status"
    echo "6. Get Lambda Details"
    echo "7. Get RDS Details"
    echo "8. Get EC2 Details"
    echo "9. Get S3 Details"
    echo "10. Get SQS Details"
    echo "11. Show Database Users"
    echo "12. Exit"
    echo ""
}

main_menu() {
    while true; do
        show_menu
        read -p "Select an option (1-12): " choice
        echo ""
        
        case $choice in
            1)
                deploy_full_stack
                ;;
            2)
                deploy_infrastructure_stack
                ;;
            3)
                deploy_application_stack
                ;;
            4)
                validate_templates
                ;;
            5)
                display_all_stack_status
                ;;
            6)
                display_lambda_details
                ;;
            7)
                display_rds_details
                ;;
            8)
                display_ec2_details
                ;;
            9)
                display_s3_details
                ;;
            10)
                display_sqs_details
                ;;
            11)
                show_database_users
                ;;
            12)
                echo "Goodbye!"
                exit 0
                ;;
            *)
                print_error "Invalid option. Please select 1-12."
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    # Check if script is run directly
    if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
        main_menu
    fi
}

# Run main function
main "$@"
