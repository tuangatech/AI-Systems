# STT WebSocket Service - AWS Deployment Guide

Complete Terraform deployment for Speech-to-Text WebSocket service using ECS Fargate, Application Load Balancer, and AWS Transcribe.

## 🏗️ AWS Components Overview

This deployment uses the following AWS services:

### Amazon ECR (Elastic Container Registry)
**What it is:** A Docker container registry to store your application images.

**What we use it for:**
- Stores your built Docker images (the packaged WebSocket service)
- ECS pulls images from here to run containers
- Automatically managed image lifecycle (keeps last 5 images)

**In this deployment:**
- Repository name: `stt-websocket-service`
- Images tagged as `:latest`

---

### Amazon ECS (Elastic Container Service) with Fargate
**What it is:** A container orchestration service that runs Docker containers without managing servers.

#### ECS Cluster
**What it is:** A logical grouping of services and tasks.

**In this deployment:**
- Cluster name: `stt-cluster`
- Acts as a container for your service

#### ECS Task Definition
**What it is:** A blueprint that describes how to run your container (like a recipe).

**Defines:**
- Which Docker image to use (from ECR)
- CPU and memory allocation (0.5 vCPU, 1GB RAM)
- Environment variables (AWS_REGION, PORT, LOG_LEVEL, etc.)
- Container port (8080)
- Health check configuration
- IAM roles for permissions

**Think of it as:** Instructions for "how to run one copy of your application"

#### ECS Service
**What it is:** Manages running tasks and ensures the desired number are always running.

**What it does:**
- Keeps 1 task running at all times (desired count = 1)
- Restarts tasks if they crash
- Performs rolling deployments when you update
- Registers tasks with the Load Balancer
- Monitors task health

**Think of it as:** The manager that ensures your application is always running

#### ECS Task (Running Container)
**What it is:** An actual running instance of your container.

**In this deployment:**
- 1 task runs your WebSocket service
- Assigned a private IP address
- Connects to ALB for incoming traffic
- Sends logs to CloudWatch
- Makes API calls to AWS Transcribe

**Think of it as:** Your actual running application

---

### Application Load Balancer (ALB)
**What it is:** A load balancer that distributes incoming traffic to your containers.

**What we use it for:**
- Provides a stable public endpoint (DNS name)
- Supports WebSocket connections (HTTP upgrade)
- Performs health checks on your containers
- Routes traffic to healthy ECS tasks only

**In this deployment:**
- Listens on port 80 (HTTP)
- Health check: `GET /health` every 30 seconds
- Target type: IP (for Fargate tasks)
- Your frontend connects to: `ws://alb-dns-name`

---

### Security Groups
**What they are:** Virtual firewalls that control network traffic.

#### ALB Security Group
**Allows:**
- Inbound: Port 80 from anywhere (0.0.0.0/0) - public access
- Outbound: All traffic (to reach ECS tasks)

#### ECS Tasks Security Group
**Allows:**
- Inbound: Port 8080 from ALB only (secure)
- Outbound: All traffic (to reach AWS Transcribe API)

---

### IAM Roles
**What they are:** AWS permissions that define what your containers can do.

#### ECS Task Execution Role (`stt-websocket-ecs-execution-role`)
**Purpose:** Allows ECS to manage your containers.

**Permissions:**
- Pull Docker images from ECR
- Send logs to CloudWatch
- Retrieve secrets (not used in POC)

**Think of it as:** Permissions for ECS to set up and run your container

#### ECS Task Role (`stt-websocket-ecs-task-role`)
**Purpose:** Allows your application code to access AWS services.

**Permissions:**
- `transcribe:StartStreamTranscription` - call AWS Transcribe API

**Think of it as:** Permissions for your application code to call other AWS services

---

### CloudWatch Logs
**What it is:** AWS logging service that stores container logs.

**In this deployment:**
- Log group: `/ecs/stt-websocket`
- Retention: 7 days
- All container stdout/stderr goes here
- Use for debugging and monitoring

---

### Amazon VPC (Virtual Private Cloud)
**What it is:** Your isolated network in AWS.

**In this deployment:**
- Uses your default VPC (already exists)
- ECS tasks run in public subnets (assigned public IPs)
- Security groups control access

---

## 🔄 How Components Work Together

```
1. User Browser (Frontend)
        ↓ WebSocket (ws://)
        
2. Application Load Balancer (Public endpoint)
   - Receives WebSocket connections
   - Performs health checks
        ↓
        
3. ECS Service (Manages deployment)
   - Ensures 1 task is always running
   - Registers task with ALB
        ↓
        
4. ECS Task (Your running container)
   - Pulled from ECR
   - Uses Task Role to call Transcribe
   - Sends logs to CloudWatch
        ↓
        
5. AWS Transcribe Streaming API
   - Converts audio to text
   - Returns transcripts
```

---

## 💰 Cost Breakdown

| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| **ECR** | < 5 images, ~500MB | ~$0.50 |
| **ECS Fargate** | 0.5 vCPU, 1GB, 24/7 | ~$15.00 |
| **ALB** | 1 load balancer | ~$16.00 |
| **CloudWatch Logs** | 7-day retention, ~1GB | ~$0.50 |
| **Data Transfer** | Minimal for POC | ~$1.00 |
| **AWS Transcribe** | Pay per use | $0.024/min |
| **Total Base Cost** | (excluding Transcribe usage) | **~$33/month** |

---

## 📋 Prerequisites

Before starting, ensure you have:

- **AWS CLI** installed and configured
  ```bash
  aws configure
  # Enter your AWS Access Key ID, Secret Access Key, and default region (us-east-1)
  ```
- **Terraform** installed (version >= 1.0)
  ```bash
  terraform --version
  ```
- **Docker** installed and running
  ```bash
  docker --version
  ```
- Your **application code with Dockerfile** in the same directory as these Terraform files

## 🏗️ Architecture Overview

```
User Browser 
    ↓ (HTTPS)
CloudFront (Frontend)
    ↓ (ws://)
Application Load Balancer
    ↓
ECS Fargate Tasks
    ↓
AWS Transcribe Streaming API
```

### AWS Resources Created

- **ECR Repository** - Store Docker images
- **ECS Fargate Cluster** - Run containers serverlessly
- **Application Load Balancer** - HTTP/WebSocket endpoint
- **Security Groups** - Network access controls
- **IAM Roles** - AWS Transcribe permissions
- **CloudWatch Logs** - Container logging (7-day retention)

## 🚀 Deployment Steps

### Step 1: Initialize Terraform

```bash
terraform init
```

This downloads the AWS provider and prepares your directory.

**Expected output:**
```
Terraform has been successfully initialized!
```

Optional: as I created a ECR repo and pushed the Docker image manually already. # 2. Import your existing ECR repository into Terraform state

```bash
terraform import aws_ecr_repository.stt_service stt-websocket-service
```
 

### Step 2: Review Infrastructure Plan

```bash
terraform plan
```

This shows you all resources that will be created. Review carefully.

**You should see:**
- 1 ECR repository
- 1 ECS cluster
- 1 ECS service
- 1 ECS task definition
- 1 Application Load Balancer
- 1 Target group
- 2 Security groups
- 2 IAM roles
- 1 CloudWatch log group

### Step 3: Deploy Infrastructure

```bash
terraform apply
```

Type `yes` when prompted.

**This takes approximately 3-5 minutes** and creates all AWS resources.

**Expected output:**
```
Apply complete! Resources: 15 added, 0 changed, 0 destroyed.

Outputs:
alb_dns_name = "stt-websocket-alb-1817666409.us-east-1.elb.amazonaws.com"
alb_url = "http://stt-websocket-alb-1817666409.us-east-1.elb.amazonaws.com"
cloudwatch_log_group = "/ecs/stt-websocket"
ecr_repository_name = "stt-websocket-service"
ecr_repository_url = "418272790285.dkr.ecr.us-east-1.amazonaws.com/stt-websocket-service"
ecs_cluster_name = "stt-cluster"
ecs_service_name = "stt-websocket-service"
execution_role_arn = "arn:aws:iam::418272790285:role/stt-websocket-ecs-execution-role"
target_group_arn = "arn:aws:elasticloadbalancing:us-east-1:418272790285:targetgroup/stt-websocket-tg/d916d31dbccdce14"
task_role_arn = "arn:aws:iam::418272790285:role/stt-websocket-ecs-task-role"
websocket_endpoint = "ws://stt-websocket-alb-1817666409.us-east-1.elb.amazonaws.com"
```

### Step 4: Build and Deploy Your Application

Make the deployment script executable:
```bash
chmod +x deploy.sh
```

Run the deployment:
```bash
./deploy.sh
```

**This script automatically:**
1. ✅ Checks Terraform state
2. ✅ Authenticates Docker to ECR
3. ✅ Builds your Docker image
4. ✅ Pushes image to ECR
5. ✅ Triggers ECS service update

**Expected output:**
```
=== STT WebSocket Service Deployment ===
✓ Docker image pushed to ECR
✓ ECS service update triggered
🎉 DEPLOYMENT SUCCESSFUL 🎉
```

### Step 5: Verify Deployment

Wait 2-5 minutes for ECS to pull and deploy your container.

**Check service status:**
```bash
aws ecs describe-services \
  --cluster stt-cluster \
  --services stt-websocket-service \
  --region us-east-1 \
  --query 'services[0].[status,runningCount,desiredCount,deployments[0].status]'
```

Expected output: ["ACTIVE", 1, 1, "PRIMARY"] which is ECS server is running

**Test health endpoint:**
```bash
curl http://$(terraform output -raw alb_dns_name)/health
```

**Expected response:**
```json
{"status":"healthy","timestamp":"2025-12-31T20:06:38.939Z","region":"us-east-1","uptime":508.404032818}
```

### Step 6: Get Your WebSocket Endpoint

```bash
terraform output websocket_endpoint
```

**Use this URL in your React frontend:**
```javascript
const WS_URL = "ws://stt-websocket-alb-1817666409.us-east-1.elb.amazonaws.com";
```

## 🔧 Configuration

### Customizing Resources

Edit values in `main.tf` (Variables section):

```hcl
variable "ecs_task_cpu" {
  default     = "512"  # 512 = 0.5 vCPU, 1024 = 1 vCPU, 2048 = 2 vCPU
}

variable "ecs_task_memory" {
  default     = "1024"  # Memory in MB
}

variable "ecs_desired_count" {
  default     = 1  # Number of running tasks
}

variable "log_level" {
  default     = "INFO"  # ERROR, WARN, INFO, DEBUG
}
```

After changes:
```bash
terraform apply
./deploy.sh  # Redeploy application
```

## 📊 Monitoring & Troubleshooting

### View Container Logs (Live)

```bash
aws logs tail /ecs/stt-websocket --follow --region us-east-1
```

### View Recent Logs

```bash
aws logs tail /ecs/stt-websocket --since 10m --region us-east-1
```

### Check ECS Service Status

```bash
aws ecs describe-services \
  --cluster stt-cluster \
  --services stt-websocket-service \
  --region us-east-1
```

### Check Target Health

```bash
aws elbv2 describe-target-health \
  --target-group-arn $(terraform output -raw target_group_arn) \
  --region us-east-1
```

### Check Running Tasks

```bash
aws ecs list-tasks \
  --cluster stt-cluster \
  --service-name stt-websocket-service \
  --region us-east-1
```

## 🐛 Common Issues & Solutions

### Issue 1: ECS Task Keeps Restarting

**Symptoms:** Service shows 0 running tasks

**Check logs:**
```bash
aws logs tail /ecs/stt-websocket --since 30m --region us-east-1
```

**Common causes:**
- ❌ No Docker image in ECR → Run `./deploy.sh`
- ❌ Health check failing → Verify `/health` endpoint returns 200
- ❌ Port mismatch → Ensure container exposes port 8080
- ❌ Application crash → Check CloudWatch logs for errors

### Issue 2: "Cannot Pull Container Image"

**Solution:**
```bash
# Verify image exists in ECR
aws ecr describe-images \
  --repository-name stt-websocket-service \
  --region us-east-1

# If no images, run deployment
./deploy.sh
```

### Issue 3: WebSocket Connection Fails

**Check 1: Verify ALB is healthy**
```bash
curl http://$(terraform output -raw alb_dns_name)/health
```

**Check 2: Verify security groups**
```bash
# ALB should allow port 80 inbound
# ECS tasks should allow port 8080 from ALB
terraform show | grep -A 10 "security_group"
```

**Check 3: Test WebSocket connection**
```bash
# Install wscat if needed: npm install -g wscat
wscat -c $(terraform output -raw websocket_endpoint)
```

### Issue 4: Permission Errors (Transcribe)

**Verify IAM role has permissions:**
```bash
aws iam get-role-policy \
  --role-name stt-websocket-ecs-task-role \
  --policy-name TranscribeAccess
```

**Should show:**
```json
{
  "Action": ["transcribe:StartStreamTranscription"],
  "Effect": "Allow",
  "Resource": "*"
}
```

### Issue 5: Terraform Apply Fails

**Common errors:**

**"VPC not found"**
```bash
# Verify default VPC exists
aws ec2 describe-vpcs --filters "Name=isDefault,Values=true"
```

**"No subnets found"**
```bash
# Check subnets in default VPC
aws ec2 describe-subnets --filters "Name=vpc-id,Values=<vpc-id>"
```

**"Role already exists"**
```bash
# Import existing role
terraform import aws_iam_role.ecs_task_role stt-websocket-ecs-task-role
```

## 🔄 Redeployment (After Code Changes)

After modifying your application code:

```bash
./deploy.sh
```

This automatically:
- Rebuilds Docker image
- Pushes to ECR
- Triggers ECS rolling deployment

**No downtime** - ECS performs a rolling update.

## 📈 Viewing All Terraform Outputs

```bash
# View all outputs
terraform output

# Get specific values
terraform output ecr_repository_url
terraform output alb_dns_name
terraform output websocket_endpoint
terraform output cloudwatch_log_group
```

## 💰 Cost Estimate

Approximate monthly costs for POC usage (light traffic):

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| **ECS Fargate** | 0.5 vCPU, 1GB RAM, 24/7 | ~$15 |
| **Application Load Balancer** | 1 ALB | ~$16 |
| **AWS Transcribe** | Pay-per-use | $0.024/minute |
| **CloudWatch Logs** | 7-day retention | ~$0.50 |
| **ECR Storage** | < 5 images | ~$0.50 |

**Total: ~$32-35/month** + transcription usage

### Cost Optimization Tips

**Stop service when not in use:**
```bash
# Set desired count to 0
terraform apply -var="ecs_desired_count=0"

# Restart when needed
terraform apply -var="ecs_desired_count=1"
```

**Reduce logging:**
```hcl
# In main.tf, change CloudWatch retention
retention_in_days = 1  # Instead of 7
```

## 🗑️ Cleanup (Destroy All Resources)

When you're done with the POC:

```bash
terraform destroy
```

Type `yes` to confirm.

**This will delete:**
- ✅ ECS Service & Cluster
- ✅ Application Load Balancer
- ✅ Security Groups
- ✅ IAM Roles
- ✅ ECR Repository (and all images)
- ✅ CloudWatch Logs

**⚠️ Warning:** ECR images will be permanently deleted. Back up if needed.

## 🔐 Security Notes (POC)

This is a **POC configuration** with simplified security:

- ❌ No authentication on WebSocket endpoint
- ❌ HTTP-only (not HTTPS)
- ❌ No WAF or DDoS protection
- ❌ Public subnets for ECS tasks
- ❌ No rate limiting

**For production, you should add:**
- ✅ ACM SSL certificate for HTTPS
- ✅ Authentication/authorization
- ✅ AWS WAF on ALB
- ✅ Private subnets with NAT Gateway
- ✅ API Gateway for rate limiting
- ✅ CloudWatch alarms

## 📚 Additional Resources

### AWS Documentation
- [ECS Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [AWS Transcribe Streaming](https://docs.aws.amazon.com/transcribe/latest/dg/streaming.html)
- [Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/)

### Terraform Resources
- [AWS Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform State Management](https://www.terraform.io/docs/language/state/index.html)

## 🆘 Getting Help

**View Terraform state:**
```bash
terraform show
```

**Check what resources exist:**
```bash
terraform state list
```

**Debug Terraform:**
```bash
TF_LOG=DEBUG terraform apply
```

**AWS Support:**
```bash
aws sts get-caller-identity  # Verify AWS credentials
aws configure list            # Show current configuration
```

## 📝 Frontend Integration Example

```javascript
// React component example
import { useEffect, useState } from 'react';

const WEBSOCKET_URL = "ws://your-alb-dns-name.us-east-1.elb.amazonaws.com";

function VoiceInput() {
  const [transcript, setTranscript] = useState('');
  const [ws, setWs] = useState(null);

  useEffect(() => {
    const websocket = new WebSocket(WEBSOCKET_URL);
    
    websocket.onopen = () => {
      console.log('Connected to STT service');
    };
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'partial') {
        setTranscript(data.text); // Show partial
      } else if (data.type === 'final') {
        setTranscript(data.text); // Show final
      }
    };
    
    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    setWs(websocket);
    
    return () => websocket.close();
  }, []);

  return (
    <div>
      <p>Transcript: {transcript}</p>
    </div>
  );
}
```

## 🎉 Success Checklist

- ✅ `terraform init` completed
- ✅ `terraform apply` created 15 resources
- ✅ `./deploy.sh` pushed Docker image
- ✅ Health endpoint returns `{"status": "healthy"}`
- ✅ CloudWatch logs show container running
- ✅ WebSocket connection test successful
- ✅ Frontend can connect to WebSocket endpoint

---

**You're all set!** Your STT WebSocket service is deployed and ready for frontend integration. 🚀