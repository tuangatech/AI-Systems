#!/bin/bash

# Deployment script for STT WebSocket Service
# This script builds and pushes the Docker image to ECR after Terraform applies

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="us-east-1"
DOCKERFILE_PATH="../backend-stt-service"  # Assumes Dockerfile is in backend-stt-service directory

echo -e "${GREEN}=== STT WebSocket Service Deployment ===${NC}\n"

# Step 1: Check if Terraform has been applied
echo -e "${YELLOW}Step 1: Checking Terraform state...${NC}"
if [ ! -f "terraform.tfstate" ]; then
    echo -e "${RED}Error: terraform.tfstate not found.${NC}"
    echo -e "${RED}Please run 'terraform apply' first to create the infrastructure.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Terraform state found${NC}\n"

# Step 2: Get ECR repository URL from Terraform outputs
echo -e "${YELLOW}Step 2: Retrieving ECR repository URL...${NC}"
ECR_REPOSITORY_URL=$(terraform output -raw ecr_repository_url 2>/dev/null)

if [ -z "$ECR_REPOSITORY_URL" ]; then
    echo -e "${RED}Error: Could not retrieve ECR repository URL from Terraform outputs.${NC}"
    echo -e "${RED}Make sure you have run 'terraform apply' successfully first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ ECR Repository URL: $ECR_REPOSITORY_URL${NC}\n"

# Step 3: Check if Dockerfile exists
echo -e "${YELLOW}Step 3: Checking for Dockerfile...${NC}"
if [ ! -f "$DOCKERFILE_PATH/Dockerfile" ]; then
    echo -e "${RED}Error: Dockerfile not found in $DOCKERFILE_PATH${NC}"
    echo -e "${RED}Please ensure your Dockerfile exists in the current directory.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Dockerfile found${NC}\n"

# Step 4: Authenticate Docker to ECR
echo -e "${YELLOW}Step 4: Authenticating Docker to ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_REPOSITORY_URL

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to authenticate Docker to ECR.${NC}"
    echo -e "${RED}Make sure AWS CLI is configured: aws configure${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker authenticated to ECR${NC}\n"

# Step 5: Build Docker image
echo -e "${YELLOW}Step 5: Building Docker image...${NC}"
echo -e "${BLUE}This may take a few minutes...${NC}"
docker build -t stt-websocket-service:latest $DOCKERFILE_PATH

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Docker build failed.${NC}"
    echo -e "${RED}Please check your Dockerfile for errors.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker image built successfully${NC}\n"

# Step 6: Tag Docker image for ECR
echo -e "${YELLOW}Step 6: Tagging Docker image...${NC}"
docker tag stt-websocket-service:latest $ECR_REPOSITORY_URL:latest

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to tag Docker image.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker image tagged${NC}\n"

# Step 7: Push Docker image to ECR
echo -e "${YELLOW}Step 7: Pushing Docker image to ECR...${NC}"
echo -e "${BLUE}This may take a few minutes depending on image size...${NC}"
docker push $ECR_REPOSITORY_URL:latest

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to push Docker image to ECR.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker image pushed to ECR${NC}\n"

# Step 8: Force new deployment in ECS
echo -e "${YELLOW}Step 8: Triggering ECS service update...${NC}"
ECS_CLUSTER=$(terraform output -raw ecs_cluster_name 2>/dev/null)
ECS_SERVICE=$(terraform output -raw ecs_service_name 2>/dev/null)

if [ -z "$ECS_CLUSTER" ] || [ -z "$ECS_SERVICE" ]; then
    echo -e "${RED}Error: Could not retrieve ECS cluster or service name.${NC}"
    exit 1
fi

aws ecs update-service \
    --cluster $ECS_CLUSTER \
    --service $ECS_SERVICE \
    --force-new-deployment \
    --region $AWS_REGION \
    > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to update ECS service.${NC}"
    echo -e "${RED}The image was pushed successfully, but ECS update failed.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ ECS service update triggered${NC}\n"

# Step 9: Display deployment information
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          🎉 DEPLOYMENT SUCCESSFUL 🎉                      ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${YELLOW}📍 Important URLs:${NC}"
echo -e "   ${BLUE}ALB URL:${NC}        $(terraform output -raw alb_url)"
echo -e "   ${BLUE}WebSocket URL:${NC}  $(terraform output -raw websocket_endpoint)"
echo -e "   ${BLUE}Health Check:${NC}   $(terraform output -raw alb_url)/health"

echo -e "\n${YELLOW}📊 Monitor Deployment:${NC}"
echo -e "   aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION"

echo -e "\n${YELLOW}📝 View Logs:${NC}"
echo -e "   aws logs tail $(terraform output -raw cloudwatch_log_group) --follow --region $AWS_REGION"

echo -e "\n${YELLOW}⏱️  Deployment Timeline:${NC}"
echo -e "   ${BLUE}•${NC} ECS will pull the new image and start a new task"
echo -e "   ${BLUE}•${NC} Health checks will verify the new task is healthy"
echo -e "   ${BLUE}•${NC} Old task will be drained and stopped"
echo -e "   ${BLUE}•${NC} Estimated time: ${GREEN}2-5 minutes${NC}"

echo -e "\n${YELLOW}🔍 Check Deployment Status:${NC}"
echo -e "   aws ecs describe-services \\"
echo -e "     --cluster $ECS_CLUSTER \\"
echo -e "     --services $ECS_SERVICE \\"
echo -e "     --query 'services[0].deployments' \\"
echo -e "     --region $AWS_REGION"

echo -e "\n${GREEN}✅ Your WebSocket service will be live in a few minutes!${NC}\n"