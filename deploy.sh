#!/bin/bash

STACK_NAME=ftp-transformer
PROFILE=marium
REGION=us-east-1
KEY_NAME=marium-key

# Check if key pair exists and create if it doesn't
echo "Checking if key pair '$KEY_NAME' exists..."
KEY_PAIR_EXISTS=$(aws ec2 describe-key-pairs \
  --key-names "$KEY_NAME" \
  --profile "$PROFILE" \
  --region "$REGION" \
  --query 'KeyPairs[0].KeyName' \
  --output text 2>/dev/null)

if [ $? -eq 0 ] && [ "$KEY_PAIR_EXISTS" == "$KEY_NAME" ]; then
  echo "✅ Key pair '$KEY_NAME' already exists."
else
  echo "Key pair '$KEY_NAME' does not exist. Creating..."
  aws ec2 create-key-pair \
    --key-name "$KEY_NAME" \
    --query 'KeyMaterial' \
    --output text \
    --profile "$PROFILE" \
    --region "$REGION" > "$KEY_NAME.pem"
  
  if [ $? -eq 0 ]; then
    echo "✅ Key pair '$KEY_NAME' has been successfully created and saved to '$KEY_NAME.pem'"
    chmod 400 "$KEY_NAME.pem"
    echo "✅ Set proper permissions (400) on '$KEY_NAME.pem'"
  else
    echo "❌ Failed to create key pair '$KEY_NAME'"
    exit 1
  fi
fi

# Check if stack exists and get its status
echo "Checking stack status: $STACK_NAME"
STACK_STATUS=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --profile "$PROFILE" \
  --region "$REGION" \
  --query 'Stacks[0].StackStatus' \
  --output text 2>/dev/null)

if [ $? -eq 0 ]; then
  echo "Stack exists with status: $STACK_STATUS"
  
  # Check if stack status indicates it's not in a successful state
  if [[ "$STACK_STATUS" == *"COMPLETE"* ]] && [[ "$STACK_STATUS" != *"ROLLBACK"* ]]; then
    echo "✅ Stack '$STACK_NAME' is in a successful state. Skipping deletion."
  else
    echo "Stack is not in a successful state. Proceeding with deletion..."
    echo "Deleting stack: $STACK_NAME"
    aws cloudformation delete-stack \
      --stack-name "$STACK_NAME" \
      --profile "$PROFILE" \
      --region "$REGION"

    echo "Waiting for stack to be deleted..."
    aws cloudformation wait stack-delete-complete \
      --stack-name "$STACK_NAME" \
      --profile "$PROFILE" \
      --region "$REGION"

    if [ $? -eq 0 ]; then
      echo "✅ Stack '$STACK_NAME' has been successfully deleted."
    else
      echo "❌ Stack deletion failed or timed out."
      exit 1
    fi
  fi
else
  echo "Stack '$STACK_NAME' does not exist. Proceeding with deployment."
fi

# Fetch default VPC ID
DEFAULT_VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --profile "$PROFILE" \
  --region "$REGION" \
  --query "Vpcs[0].VpcId" \
  --output text)

# Fetch default subnet IDs (first two for RDS subnet group, comma-separated, no spaces)
DEFAULT_SUBNET_IDS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$DEFAULT_VPC_ID" \
  --profile "$PROFILE" \
  --region "$REGION" \
  --query "Subnets[0:2].SubnetId" \
  --output text | xargs | tr ' ' ',')

# Get the first subnet ID for EC2
DEFAULT_SUBNET_ID=$(echo "$DEFAULT_SUBNET_IDS" | cut -d',' -f1)

# Fetch default security group ID
DEFAULT_SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=vpc-id,Values=$DEFAULT_VPC_ID" "Name=group-name,Values=default" \
  --profile "$PROFILE" \
  --region "$REGION" \
  --query "SecurityGroups[0].GroupId" \
  --output text)

echo "Deploying stack: $STACK_NAME"
sam build --profile "$PROFILE"
sam deploy --profile "$PROFILE" \
  --parameter-overrides \
    DefaultVpcId="$DEFAULT_VPC_ID" \
    DefaultSubnetId="$DEFAULT_SUBNET_ID" \
    DefaultSubnetIds="$DEFAULT_SUBNET_IDS" \
    DefaultSecurityGroupId="$DEFAULT_SG_ID"
