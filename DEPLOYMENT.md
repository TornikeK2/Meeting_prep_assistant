# Meeting Prep Assistant - Cloud Deployment Guide

Quick guide to deploy to Google Cloud Run for your PM demo.

## Prerequisites

- Google Cloud account
- `gcloud` CLI installed ([Install here](https://cloud.google.com/sdk/docs/install))
- Docker installed (for local testing, optional)

---

## Step 1: GCP Console Setup (10 minutes)

### 1.1 Create/Select GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Note your **Project ID** (you'll need this)

### 1.2 Enable APIs

Go to **APIs & Services > Library** and enable:
- ✅ Google Calendar API
- ✅ Gmail API
- ✅ Cloud Run API
- ✅ Cloud Build API

### 1.3 Create OAuth Credentials

1. Go to **APIs & Services > Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. Configure OAuth consent screen if prompted (Internal is fine)
4. Application type: **Desktop app**
5. Name: `meeting-prep-assistant-local`
6. Click **CREATE**
7. **Download JSON** and save as `config/credentials.json`

### 1.4 Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click **Create API Key**
3. Copy the key

---

## Step 2: Local Authentication (5 minutes)

You need to authenticate locally first to generate the token file.

### 2.1 Update Configuration

```bash
# Update .env with your Gemini API key
GEMINI_API_KEY=your_actual_gemini_key_here
```

### 2.2 Replace credentials.json

Replace `config/credentials.json` with the file you downloaded from GCP Console.

### 2.3 Authenticate

```bash
# Install dependencies
pip install -r requirements.txt

# Run authentication (this will open browser)
python src/main.py
```

This will:
- Open browser for OAuth consent
- Generate `config/token.pickle`
- Run once to test the app

**Important**: You need `token.pickle` file for cloud deployment!

---

## Step 3: Deploy to Cloud Run (5 minutes)

### Option A: Using Deploy Script (Easiest)

```bash
# Make script executable (Mac/Linux)
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

### Option B: Manual Deployment (Windows)

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com

# Deploy
gcloud run deploy meeting-prep-assistant \
    --source . \
    --region=us-central1 \
    --platform=managed \
    --allow-unauthenticated \
    --memory=512Mi \
    --timeout=300
```

---

## Step 4: Test Deployment (2 minutes)

```bash
# Get service URL
gcloud run services describe meeting-prep-assistant \
    --region=us-central1 \
    --format="value(status.url)"

# Trigger the service
curl [SERVICE_URL]
```

Or visit the URL in your browser.

---

## For Your PM Demo

### What to Show

1. **The Problem**: Manual meeting prep is time-consuming
2. **The Solution**: Automated assistant that:
   - Monitors your calendar
   - Identifies important meetings (especially client meetings)
   - Finds relevant emails automatically
   - Generates prep summaries

3. **Live Demo**:
   ```bash
   # Show it running locally
   python src/main.py

   # Show cloud deployment
   curl [YOUR_CLOUD_RUN_URL]
   ```

4. **Key Features**:
   - ✅ Smart client meeting detection
   - ✅ Email relevance scoring
   - ✅ Priority-based filtering
   - ✅ Cloud-ready architecture
   - 🚧 Gemini AI integration (in progress)

### Demo Script

```
"This Meeting Prep Assistant monitors my Google Calendar and automatically
prepares briefings for upcoming meetings. It's particularly smart about
identifying client meetings - those with external attendees - and prioritizes
them.

For each meeting, it searches my Gmail for relevant context: emails from
attendees, related threads, and key discussions. It uses a relevance scoring
algorithm that considers attendee matches, keywords, recency, and thread
activity.

The app is deployed on Google Cloud Run, making it serverless and scalable.
Currently it generates structured summaries, and I'm integrating Gemini AI
for natural language briefings.

Let me show you it running..."
```

---

## Troubleshooting

### "OAuth redirect error"
- Cloud Run needs pre-authenticated `token.pickle`
- Run locally first to generate it

### "APIs not enabled"
- Go to GCP Console and enable Calendar + Gmail APIs

### "Permission denied"
- Check OAuth scopes in `src/utils/auth.py`
- Regenerate credentials if needed

### "Module not found"
- Ensure all files copied: `src/`, `config/`, `.env`
- Check Dockerfile includes all directories

---

## Cost Estimate

- **Cloud Run**: ~$0-2/month (minimal usage)
- **API Calls**: Free tier (personal use)
- **Gemini API**: Pay-per-token (minimal for testing)

**Total**: Essentially free for demo purposes

---

## Next Steps After Demo

1. Add Gemini AI integration for smart summaries
2. Implement Cloud Scheduler for automatic runs
3. Add email notification/sending
4. Create web dashboard for viewing prep reports
5. Add meeting notes extraction
6. Integrate with other tools (Slack, Drive, etc.)

---

## Quick Commands Cheat Sheet

```bash
# Local test
python src/main.py

# Deploy to Cloud Run
./deploy.sh

# View logs
gcloud run logs read meeting-prep-assistant --region=us-central1

# Update deployment
gcloud run deploy meeting-prep-assistant --source .

# Delete service
gcloud run services delete meeting-prep-assistant --region=us-central1
```

Good luck with your demo! 🚀