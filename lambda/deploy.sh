#!/bin/bash
# AWS Lambda Container Deployment Script
set -e

# Configuration (or override via environment variables)
AWS_REGION=${AWS_REGION:-"ap-south-1"}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO_NAME=${ECR_REPOSITORY:-"smart-attendance-lambda"}
IMAGE_TAG=${IMAGE_TAG:-"latest"}
LAMBDA_FUNCTION_NAME=${LAMBDA_FUNCTION_NAME:-"smart-attendance"}

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo "=========================================================="
echo " Deploying Smart Attendance to AWS Lambda via ECR"
echo " AWS Account: $AWS_ACCOUNT_ID | Region: $AWS_REGION"
echo " ECR Target:  $ECR_URI:$IMAGE_TAG"
echo "=========================================================="

# 1. Authenticate Docker with Amazon ECR
echo "[1/4] Authenticating with Amazon ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# 2. Check if ECR repo exists, create if not
echo "[2/4] Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --region "$AWS_REGION" || \
aws ecr create-repository --repository-name "$ECR_REPO_NAME" --region "$AWS_REGION" --image-scanning-configuration scanOnPush=true

# 3. Build & Tag Docker Image
echo "[3/4] Building Docker Container Image..."
docker build -t "$ECR_REPO_NAME:$IMAGE_TAG" -f lambda/Dockerfile .
docker tag "$ECR_REPO_NAME:$IMAGE_TAG" "$ECR_URI:$IMAGE_TAG"

# 4. Push Image to ECR
echo "[4/4] Pushing Container Image to ECR..."
docker push "$ECR_URI:$IMAGE_TAG"

# 5. Update Lambda Function Code if function exists
echo "Updating Lambda function code..."
aws lambda update-function-code \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --image-uri "$ECR_URI:$IMAGE_TAG" \
    --region "$AWS_REGION" || echo "Lambda function does not exist yet. Run infrastructure/setup-aws.sh to provision it."

echo "Deployment finished successfully!"
