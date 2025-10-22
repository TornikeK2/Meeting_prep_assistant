#!/bin/bash

# Meeting Prep Assistant - Cloud Run Deployment Script
# Quick deployment to Google Cloud Run

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Meeting Prep Assistant Deployer${NC}"
echo -e "${GREEN}================================${NC}\n"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not found${NC}"
    echo "Please install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get GCP project ID
echo -e "${YELLOW}Enter your GCP Project ID:${NC}"
read -r PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: Project ID cannot be empty${NC}"
    exit 1
fi

# Set project
echo -e "\n${YELLOW}Setting GCP project...${NC}"
gcloud config set project "$PROJECT_ID"

# Get region
echo -e "\n${YELLOW}Enter region (e.g., us-central1):${NC}"
read -r REGION

if [ -z "$REGION" ]; then
    REGION="us-central1"
    echo "Using default: $REGION"
fi

# Service name
SERVICE_NAME="meeting-prep-assistant"

echo -e "\n${YELLOW}Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable calendar-json.googleapis.com
gcloud services enable gmail.googleapis.com

echo -e "\n${YELLOW}Building and deploying to Cloud Run...${NC}"
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region="$REGION" \
    --platform=managed \
    --allow-unauthenticated \
    --memory=512Mi \
    --cpu=1 \
    --timeout=300 \
    --max-instances=1

echo -e "\n${GREEN}✓ Deployment complete!${NC}"
echo -e "\n${YELLOW}Service URL:${NC}"
gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format="value(status.url)"

echo -e "\n${YELLOW}To trigger the service manually:${NC}"
echo "curl \$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')"

echo -e "\n${GREEN}Deployment successful!${NC}"