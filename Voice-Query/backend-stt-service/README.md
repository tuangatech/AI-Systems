# STT WebSocket Service

WebSocket service for streaming audio to AWS Transcribe. Deployed on ECS Fargate with Application Load Balancer.

---

## **Architecture**

```
Client (React) → ALB (WebSocket) → ECS Fargate → AWS Transcribe
```

---

## **Prerequisites**

- AWS CLI configured with credentials
- Docker installed locally
- AWS Account with permissions for:
  - ECR (push images)
  - ECS (create tasks/services)
  - ALB (create load balancer)
  - IAM (create roles)

---

## **Local Development**

### **1. Install Dependencies**

```bash
cd backend-stt-service
npm install
```

### **2. Set Environment Variables**

Create `.env` file:

```bash
AWS_REGION=us-east-1
PORT=8080
LOG_LEVEL=DEBUG
```

### **3. Run Locally**

```bash
# Development mode (auto-restart on changes)
npm run dev

# Production mode
npm start
```

### **4. Test WebSocket Connection**

Install `wscat`:
```bash
npm install -g wscat
```

Connect to local server:
```bash
wscat -c ws://localhost:8080
```

---

## **Deployment to AWS**

### **Step 1: Create ECR Repository**

```bash
aws configure
```

```bash
# Set variables
AWS_REGION=us-east-1
ECR_REPO_NAME=stt-websocket-service

# Create ECR repository
aws ecr create-repository \
  --repository-name $ECR_REPO_NAME \
  --region $AWS_REGION

# Get repository URI
ECR_URI=$(aws ecr describe-repositories \
  --repository-names $ECR_REPO_NAME \
  --region $AWS_REGION \
  --query 'repositories[0].repositoryUri' \
  --output text)

echo "ECR Repository: $ECR_URI"
```

---

### **Step 2: Build and Push Docker Image**
Create a Node.js container for your WebSocket/AWS Transcribe proxy service. 
- Create a non-root user `nodejs`, changes ownership of `/app` to this user. If container is compromised, attacker has limited privileges
- ECS does health check every 30 seconds to determine container health
- Starts the application "src/server.js" when container launches.
- (Start the Docker Desktop before running `docker build`)

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_URI

# Build image
docker build -t stt-websocket-service .

# Tag image
docker tag stt-websocket-service:latest $ECR_URI:latest

# Push to ECR
docker push $ECR_URI:latest
```

---

### **Step 3: Create IAM Role for ECS Task**

Create `ecs-task-role-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "transcribe:StartStreamTranscription"
      ],
      "Resource": "*"
    }
  ]
}
```

Create role:

```bash
# Create trust policy for ECS tasks
cat > ecs-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create IAM role
aws iam create-role \
  --role-name ECSTranscribeTaskRole \
  --assume-role-policy-document file://ecs-trust-policy.json

# Attach policy
aws iam put-role-policy \
  --role-name ECSTranscribeTaskRole \
  --policy-name TranscribeAccess \
  --policy-document file://ecs-task-role-policy.json

# Get role ARN
TASK_ROLE_ARN=$(aws iam get-role \
  --role-name ECSTranscribeTaskRole \
  --query 'Role.Arn' \
  --output text)

echo "Task Role ARN: $TASK_ROLE_ARN"
```

---

### **Step 4: Create ECS Cluster**

```bash
CLUSTER_NAME=stt-cluster

aws ecs create-cluster \
  --cluster-name $CLUSTER_NAME \
  --region $AWS_REGION
```

---

### **Step 5: Register Task Definition**

Create `task-definition.json`:

```json
{
  "family": "stt-websocket-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "taskRoleArn": "TASK_ROLE_ARN_PLACEHOLDER",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "stt-websocket-container",
      "image": "ECR_URI_PLACEHOLDER:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "AWS_REGION",
          "value": "us-east-1"
        },
        {
          "name": "PORT",
          "value": "8080"
        },
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/stt-websocket",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 10
      }
    }
  ]
}
```

Replace placeholders and register:

```bash
# Replace placeholders
sed -i "s|TASK_ROLE_ARN_PLACEHOLDER|$TASK_ROLE_ARN|g" task-definition.json
sed -i "s|ECR_URI_PLACEHOLDER|$ECR_URI|g" task-definition.json

# Create CloudWatch log group
aws logs create-log-group \
  --log-group-name /ecs/stt-websocket \
  --region $AWS_REGION

# Register task definition
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json \
  --region $AWS_REGION
```

---

### **Step 6: Create Application Load Balancer**

**Note:** ALB creation requires VPC, subnets, and security groups. Below is a simplified example.

```bash
# Get default VPC ID
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --query 'Vpcs[0].VpcId' \
  --output text)

# Get subnets
SUBNETS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[*].SubnetId' \
  --output text)

# Create security group for ALB
ALB_SG=$(aws ec2 create-security-group \
  --group-name stt-alb-sg \
  --description "Security group for STT ALB" \
  --vpc-id $VPC_ID \
  --query 'GroupId' \
  --output text)

# Allow HTTP traffic
aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name stt-alb \
  --subnets $SUBNETS \
  --security-groups $ALB_SG \
  --scheme internet-facing \
  --type application \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)

# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

echo "ALB DNS: $ALB_DNS"
```

---

### **Step 7: Create Target Group**

```bash
TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
  --name stt-target-group \
  --protocol HTTP \
  --port 8080 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)
```

---

### **Step 8: Create ALB Listener**

```bash
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN
```

---

### **Step 9: Create ECS Service**

```bash
# Create security group for ECS tasks
ECS_SG=$(aws ec2 create-security-group \
  --group-name stt-ecs-sg \
  --description "Security group for STT ECS tasks" \
  --vpc-id $VPC_ID \
  --query 'GroupId' \
  --output text)

# Allow traffic from ALB
aws ec2 authorize-security-group-ingress \
  --group-id $ECS_SG \
  --protocol tcp \
  --port 8080 \
  --source-group $ALB_SG

# Create ECS service
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name stt-websocket-service \
  --task-definition stt-websocket-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=$TARGET_GROUP_ARN,containerName=stt-websocket-container,containerPort=8080" \
  --region $AWS_REGION
```

---

### **Step 10: Test Deployment**

```bash
# Check service status
aws ecs describe-services \
  --cluster $CLUSTER_NAME \
  --services stt-websocket-service \
  --region $AWS_REGION

# Test health endpoint
curl http://$ALB_DNS/health

# Test WebSocket connection
wscat -c ws://$ALB_DNS
```

---

## **Environment Variables**

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `us-east-1` | AWS region for Transcribe |
| `PORT` | `8080` | Server port |
| `LOG_LEVEL` | `INFO` | Logging level (ERROR, WARN, INFO, DEBUG) |
| `CONNECTION_TIMEOUT_MS` | `35000` | Max connection duration (ms) |
| `INACTIVITY_TIMEOUT_MS` | `60000` | Max inactivity time (ms) |
| `TRANSCRIBE_TIMEOUT_MS` | `5000` | Wait time for final transcript (ms) |

---

## **WebSocket Protocol**

### **Client → Server**

**Audio Data (Binary):**
- Raw PCM audio chunks (16-bit, 16kHz, mono, little-endian)
- Send continuously while recording

**End Stream Signal (Text):**
```json
{"type": "end_stream"}
```

### **Server → Client**

**Ready Signal:**
```json
{"type": "ready", "sessionId": "abc-123"}
```

**Partial Transcript:**
```json
{"type": "partial", "text": "hello world"}
```

**Final Transcript:**
```json
{"type": "final", "text": "hello world"}
```

**Error:**
```json
{"type": "error", "message": "Transcription failed"}
```

---

## **Monitoring**

### **CloudWatch Logs**

View logs:
```bash
aws logs tail /ecs/stt-websocket --follow
```

### **ECS Service Health**

```bash
aws ecs describe-services \
  --cluster $CLUSTER_NAME \
  --services stt-websocket-service
```

---

## **Updating the Service**

```bash
# Build new image
docker build -t stt-websocket-service .

# Tag and push
docker tag stt-websocket-service:latest $ECR_URI:latest
docker push $ECR_URI:latest

# Force new deployment
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service stt-websocket-service \
  --force-new-deployment
```

---

## **Troubleshooting**

### **Connection Refused**

- Check security group allows inbound traffic
- Verify ALB listener is configured
- Check ECS task is running: `aws ecs list-tasks --cluster $CLUSTER_NAME`

### **Transcription Timeout**

- Check IAM role has `transcribe:StartStreamTranscription` permission
- Verify AWS region matches Transcribe availability
- Check CloudWatch logs for Transcribe errors

### **No Partial Transcripts**

- Verify audio format: PCM 16-bit, 16kHz, mono
- Check audio chunks are being sent (CloudWatch logs)
- Ensure VAD isn't stopping stream too early

---

## **License**

MIT