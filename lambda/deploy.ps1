# PowerShell AWS Lambda Container Deployment Script
param (
    [string]$Region = "ap-south-1",
    [string]$RepoName = "smart-attendance-lambda",
    [string]$FunctionName = "smart-attendance",
    [string]$ImageTag = "latest"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Deploying Smart Attendance to AWS Lambda via ECR" -ForegroundColor Cyan
Write-Host " Region: $Region | ECR Repo: $RepoName" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Get AWS Account ID
$AccountId = (aws sts get-caller-identity --query Account --output text)
if (-not $AccountId) {
    Write-Error "Failed to retrieve AWS Account ID. Please ensure AWS CLI is installed and configured ('aws configure')."
}

$EcrUri = "$AccountId.dkr.ecr.$Region.amazonaws.com/$RepoName"

# 2. Authenticate Docker with Amazon ECR
Write-Host "[1/4] Authenticating Docker with Amazon ECR..." -ForegroundColor Yellow
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin "$AccountId.dkr.ecr.$Region.amazonaws.com"

# 3. Create ECR repo if needed
Write-Host "[2/4] Ensuring ECR repository exists..." -ForegroundColor Yellow
$repoCheck = aws ecr describe-repositories --repository-names $RepoName --region $Region 2>$null
if (-not $repoCheck) {
    Write-Host "Creating repository $RepoName..."
    aws ecr create-repository --repository-name $RepoName --region $Region --image-scanning-configuration scanOnPush=true
}

# 4. Build and Tag Docker Image
Write-Host "[3/4] Building Docker Container Image..." -ForegroundColor Yellow
docker build -t "$RepoName`:$ImageTag" -f lambda/Dockerfile .
docker tag "$RepoName`:$ImageTag" "$EcrUri`:$ImageTag"

# 5. Push to ECR
Write-Host "[4/4] Pushing image to ECR..." -ForegroundColor Yellow
docker push "$EcrUri`:$ImageTag"

# 6. Update Lambda Function
Write-Host "Updating Lambda Function code..." -ForegroundColor Green
aws lambda update-function-code `
    --function-name $FunctionName `
    --image-uri "$EcrUri`:$ImageTag" `
    --region $Region 2>$null

Write-Host "Deployment completed successfully!" -ForegroundColor Green
