#!/bin/bash
# End-to-end AWS resource provisioning script
set -e

AWS_REGION=${AWS_REGION:-"ap-south-1"}
FUNCTION_NAME=${LAMBDA_FUNCTION_NAME:-"smart-attendance"}
ROLE_NAME="SmartAttendanceLambdaRole"
API_NAME="smart-attendance-http-api"

echo "=========================================================="
echo " Provisioning AWS Serverless Resources for Smart Attendance"
echo " Region: $AWS_REGION"
echo "=========================================================="

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/smart-attendance-lambda:latest"

# 1. Create IAM Role for Lambda
echo "[1/4] Configuring IAM Role..."
TRUST_POLICY='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "lambda.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}'

aws iam get-role --role-name "$ROLE_NAME" 2>/dev/null || \
aws iam create-role --role-name "$ROLE_NAME" --assume-role-policy-document "$TRUST_POLICY"

aws iam attach-role-policy --role-name "$ROLE_NAME" \
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
echo "IAM Role ready: $ROLE_ARN"
sleep 5

# 2. Create or update Lambda function
echo "[2/4] Creating Lambda Function..."
aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" 2>/dev/null || \
aws lambda create-function \
  --function-name "$FUNCTION_NAME" \
  --package-type Image \
  --code ImageUri="$ECR_IMAGE_URI" \
  --role "$ROLE_ARN" \
  --memory-size 3008 \
  --timeout 30 \
  --region "$AWS_REGION"

# 3. Create HTTP API Gateway (v2)
echo "[3/4] Creating HTTP API Gateway..."
API_ID=$(aws apigatewayv2 create-api \
  --name "$API_NAME" \
  --protocol-type HTTP \
  --cors-configuration "AllowOrigins=*,AllowMethods=*,AllowHeaders=*" \
  --query ApiId --output text --region "$AWS_REGION")

echo "Created API Gateway with ID: $API_ID"

# 4. Integrate Lambda with API Gateway
echo "[4/4] Integrating API Gateway with Lambda..."
LAMBDA_ARN="arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}"

INTEGRATION_ID=$(aws apigatewayv2 create-integration \
  --api-id "$API_ID" \
  --integration-type AWS_PROXY \
  --integration-uri "$LAMBDA_ARN" \
  --payload-format-version "2.0" \
  --query IntegrationId --output text --region "$AWS_REGION")

# Route: ANY /{proxy+}
aws apigatewayv2 create-route \
  --api-id "$API_ID" \
  --route-key "ANY /{proxy+}" \
  --target "integrations/$INTEGRATION_ID" \
  --region "$AWS_REGION"

# Default stage with auto-deploy
aws apigatewayv2 create-stage \
  --api-id "$API_ID" \
  --stage-name '$default' \
  --auto-deploy \
  --region "$AWS_REGION"

# Grant permission to API Gateway to invoke Lambda
aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id "apigateway-invoke-permission" \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${AWS_REGION}:${ACCOUNT_ID}:${API_ID}/*" \
  --region "$AWS_REGION" 2>/dev/null || true

API_ENDPOINT="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com"
echo "=========================================================="
echo " Deployment Complete!"
echo " Public API Gateway URL: $API_ENDPOINT"
echo " Update frontend/js/config.js with this URL when ready."
echo "=========================================================="
