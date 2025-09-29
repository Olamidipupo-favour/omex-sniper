# Omex Coin Sniper API Deployment Script for PowerShell
# Usage: .\scripts\deploy.ps1 -Environment [staging|production] -Host [host] -Username [username] -Password [password]

param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "staging",
    
    [Parameter(Mandatory=$true)]
    [string]$Host,
    
    [Parameter(Mandatory=$true)]
    [string]$Username,
    
    [Parameter(Mandatory=$true)]
    [string]$Password,
    
    [Parameter(Mandatory=$false)]
    [int]$Port = 22
)

# Colors for output
$Red = "`e[31m"
$Green = "`e[32m"
$Yellow = "`e[33m"
$Blue = "`e[34m"
$Reset = "`e[0m"

Write-Host "${Blue}🚀 Starting deployment to $Environment...${Reset}"

# Validate required environment variables
if (-not $env:GITHUB_TOKEN) {
    Write-Host "${Red}❌ GITHUB_TOKEN environment variable is required${Reset}"
    exit 1
}

if (-not $env:GITHUB_ACTOR) {
    Write-Host "${Red}❌ GITHUB_ACTOR environment variable is required${Reset}"
    exit 1
}

Write-Host "${Yellow}📦 Environment: $Environment${Reset}"
Write-Host "${Yellow}🌐 Host: $Host`:$Port${Reset}"
Write-Host "${Yellow}👤 User: $Username${Reset}"

# Check if Posh-SSH module is available
try {
    Import-Module Posh-SSH -ErrorAction Stop
} catch {
    Write-Host "${Red}❌ Posh-SSH module is not installed${Reset}"
    Write-Host "Install it with: Install-Module -Name Posh-SSH -Force"
    exit 1
}

# Create deployment script
$deployScript = @"
#!/bin/bash
echo "Login to GitHub Container Registry"
echo "$env:GITHUB_TOKEN" | docker login ghcr.io -u $env:GITHUB_ACTOR --password-stdin

echo "Pull the latest image"
docker pull ghcr.io/omex/sniper-microservice/coin-sniper-api:latest

echo "Stop existing container if running"
docker stop omex-sniper-api || true
docker rm omex-sniper-api || true

echo "Run the new container"
docker run -d \
    --name omex-sniper-api \
    --restart unless-stopped \
    -p 8000:8000 \
    -e HELIUS_API_KEY="$env:HELIUS_API_KEY" \
    -e PUMPPORTAL_API_KEY="$env:PUMPPORTAL_API_KEY" \
    -e SOLANA_TRACKER_API="$env:SOLANA_TRACKER_API" \
    -e RPC_URL="$env:RPC_URL" \
    -e DEBUG=false \
    -e PORT=8000 \
    -v `$(pwd)/logs:/app/logs \
    ghcr.io/omex/sniper-microservice/coin-sniper-api:latest

echo "Wait for health check"
sleep 10
curl -f http://localhost:8000/api/v1/health/ping || exit 1

echo "Deployment completed successfully!"
"@

try {
    Write-Host "${Blue}🔄 Deploying via SSH...${Reset}"
    
    # Create secure password
    $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    $Credential = New-Object System.Management.Automation.PSCredential($Username, $SecurePassword)
    
    # Create SSH session
    $Session = New-SSHSession -ComputerName $Host -Port $Port -Credential $Credential -AcceptKey
    
    if ($Session) {
        # Execute deployment script
        $Result = Invoke-SSHCommand -SessionId $Session.SessionId -Command "bash -s" -Input $deployScript
        
        if ($Result.ExitStatus -eq 0) {
            Write-Host "${Green}✅ Deployment completed successfully!${Reset}"
            Write-Host "${Blue}🌐 API should be available at: http://$Host`:8000${Reset}"
            Write-Host "${Blue}📊 Health check: http://$Host`:8000/api/v1/health/ping${Reset}"
            Write-Host "${Blue}📚 API docs: http://$Host`:8000/docs/${Reset}"
        } else {
            Write-Host "${Red}❌ Deployment failed${Reset}"
            Write-Host "Error: $($Result.Error)"
            exit 1
        }
        
        # Close SSH session
        Remove-SSHSession -SessionId $Session.SessionId
    } else {
        Write-Host "${Red}❌ Failed to establish SSH connection${Reset}"
        exit 1
    }
} catch {
    Write-Host "${Red}❌ Deployment failed: $($_.Exception.Message)${Reset}"
    exit 1
}
