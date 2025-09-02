# 🚀 GitHub Actions Setup for DockerHub

This guide explains how to set up the GitHub Actions workflow to automatically build and push your Docker image to DockerHub.

## 📋 Prerequisites

1. **DockerHub Account**: You need a DockerHub account
2. **Repository Access**: Your DockerHub account should have access to push to `tesals/karambula`
3. **GitHub Repository**: Your code should be in a GitHub repository

## 🔐 Setting Up GitHub Secrets

### Step 1: Get DockerHub Access Token

1. Go to [DockerHub](https://hub.docker.com/) and log in
2. Click on your username → **Account Settings**
3. Go to **Security** → **New Access Token**
4. Give it a name (e.g., "GitHub Actions")
5. Select **Read & Write** permissions
6. Click **Generate**
7. **Copy the token** (you won't see it again!)

### Step 2: Add Secrets to GitHub Repository

1. Go to your GitHub repository
2. Click **Settings** tab
3. Click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Add these two secrets:

#### Secret 1: `DOCKERHUB_USERNAME`
- **Name**: `DOCKERHUB_USERNAME`
- **Value**: Your DockerHub username (e.g., `tesals`)

#### Secret 2: `DOCKERHUB_TOKEN`
- **Name**: `DOCKERHUB_TOKEN`
- **Value**: The access token you generated in Step 1

## 🔄 How the Workflow Works

### Trigger
- **Automatic**: Runs on every push to `main` or `master` branch
- **Pull Requests**: Also runs on PRs to test builds

### What It Does
1. **Checks out** your code
2. **Sets up** Docker Buildx for efficient builds
3. **Logs in** to DockerHub using your secrets
4. **Builds** the Docker image
5. **Pushes** to DockerHub with multiple tags:
   - `latest` (for main/master branch)
   - `main-{commit-sha}` (for specific commits)
   - `{version}` (if you use semantic versioning)

## 🐳 Using the Docker Image

### Option 1: Pull and Run Manually
```bash
# Pull the latest image
docker pull tesals/karambula:latest

# Run the container
docker run -d \
  --name karambula-bot \
  -p 8001:8001 \
  -e HELIUS_API_KEY=your_key \
  -e PUMPPORTAL_API_KEY=your_key \
  -v $(pwd)/bot_config.json:/app/bot_config.json \
  tesals/karambula:latest
```

### Option 2: Use Docker Compose (Recommended)
```bash
# Make sure your .env file has the API keys
echo "HELIUS_API_KEY=your_key" > .env
echo "PUMPPORTAL_API_KEY=your_key" >> .env

# Start the service
docker-compose up -d

# Check logs
docker-compose logs -f karambula-sniper-bot
```

## 📝 Environment Variables

Create a `.env` file in your project root:

```env
# Required API Keys
HELIUS_API_KEY=your_helius_api_key_here
PUMPPORTAL_API_KEY=your_pumpportal_api_key_here

# Optional Settings
TZ=UTC
PYTHONUNBUFFERED=1
```

## 🔍 Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Check your `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets
   - Ensure the token has write permissions

2. **Build Failed**
   - Check the GitHub Actions logs for build errors
   - Ensure your Dockerfile is correct

3. **Image Not Found**
   - Wait a few minutes after the workflow completes
   - Check DockerHub for the new image

### Check Workflow Status
1. Go to your GitHub repository
2. Click **Actions** tab
3. Look for the latest workflow run
4. Click on it to see detailed logs

## 🎯 Benefits

- ✅ **Automated builds** on every code push
- ✅ **Consistent images** across environments
- ✅ **Easy deployment** with `docker-compose up`
- ✅ **Version tracking** with commit-based tags
- ✅ **No local builds** needed for deployment

## 🚀 Next Steps

1. **Push your code** to GitHub
2. **Check Actions tab** to see the workflow running
3. **Wait for completion** (usually 2-5 minutes)
4. **Pull and run** your new image!

Your KARAMBULA Sniper Bot will now automatically build and deploy to DockerHub on every push! 🎉
