# PowerShell Script for AWS Serverless Resource Provisioning
param(
    [string]$Region = "ap-south-1",
    [string]$FunctionName = "smart-attendance",
    [string]$RoleName = "SmartAttendanceLambdaRole",
    [string]$ApiName = "smart-attendance-http-api"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Provisioning AWS Serverless Resources for Smart Attendance" -ForegroundColor Cyan
Write-Host " Region: $Region" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$AccountId = (aws sts get-caller-identity --query Account --output text)
$EcrImageUri = "$AccountId.dkr.ecr.$Region.amazonaws.com/smart-attendance-lambda:latest"

# 1. IAM Role
Write-Host "[1/4] Configuring IAM Role..." -ForegroundColor Yellow
$TrustPolicy = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

$roleCheck = aws iam get-role --role-name $RoleName 2>$null
if (-not $roleCheck) {
    aws iam create-role --role-name $RoleName --assume-role-policy-document $TrustPolicy
    aws iam attach-role-policy --role-name $RoleName --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

$RoleArn = "arn:aws:iam::$AccountId`:role/$RoleName"
Start-Sleep -Seconds 5

# 2. Lambda Function
Write-Host "[2/4] Configuring Lambda Function..." -ForegroundColor Yellow
$fnCheck = aws lambda get-function --function-name $FunctionName --region $Region 2>$null
if (-not $fnCheck) {
    aws lambda create-function `
        --function-name $FunctionName `
        --package-type Image `
        --code ImageUri=$EcrImageUri `
        --role $RoleArn `
        --memory-size 3008 `
        --timeout 30 `
        --region $Region
}

# 3. HTTP API Gateway (v2)
Write-Host "[3/4] Creating HTTP API Gateway..." -ForegroundColor Yellow
$ApiId = (aws apigatewayv2 create-api `
    --name $ApiName `
    --protocol-type HTTP `
    --cors-configuration "AllowOrigins=*,AllowMethods=*,AllowHeaders=*" `
    --query ApiId --output text --region $Region)

# 4. Integrate Lambda
Write-Host "[4/4] Integrating API Gateway with Lambda..." -ForegroundColor Yellow
$LambdaArn = "arn:aws:lambda:$Region`:$AccountId`:function:$FunctionName"

$IntegrationId = (aws apigatewayv2 create-integration `
    --api-id $ApiId `
    --integration-type AWS_PROXY `
    --integration-uri $LambdaArn `
    --payload-format-version "2.0" `
    --query IntegrationId --output text --region $Region)

aws apigatewayv2 create-route `
    --api-id $ApiId `
    --route-key "ANY /{proxy+}" `
    --target "integrations/$IntegrationId" `
    --region $Region

aws apigatewayv2 create-stage `
    --api-id $ApiId `
    --stage-name '$default' `
    --auto-deploy `
    --region $Region

aws lambda add-permission `
    --function-name $FunctionName `
    --statement-id "apigateway-invoke-permission" `
    --action lambda:InvokeFunction `
    --principal apigateway.amazonaws.com `
    --source-arn "arn:aws:execute-api:$Region`:$AccountId`:$ApiId/*" `
    --region $Region 2>$null

$ApiEndpoint = "https://$ApiId.execute-api.$Region.amazonaws.com"
Write-Host "==========================================================" -ForegroundColor Green
Write-Host " Deployment Complete!" -ForegroundColor Green
Write-Host " Public API Gateway URL: $ApiEndpoint" -ForegroundColor Green
Write-Host " Update frontend/js/config.js with this URL when ready." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
