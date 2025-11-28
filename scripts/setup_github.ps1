################################################################################
# GitHub Setup Script - Windows PowerShell
#
# This script helps you safely upload the GEX collector to GitHub
# as a PRIVATE repository.
#
# Prerequisites:
# - Git installed on Windows (download from https://git-scm.com)
# - GitHub account created (johnsondatascience)
#
# Usage:
#   cd c:\Users\johnsnmi\gextr
#   .\scripts\setup_github.ps1
#
################################################################################

$ErrorActionPreference = "Stop"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "GEX COLLECTOR - GITHUB SETUP" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check if git is installed
try {
    $gitVersion = git --version
    Write-Host "✓ Git is installed: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Git is not installed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Git from: https://git-scm.com/download/win"
    Write-Host "Then run this script again."
    exit 1
}

Write-Host ""
Write-Host "IMPORTANT SECURITY CHECKS" -ForegroundColor Yellow
Write-Host "==================================" -ForegroundColor Yellow
Write-Host ""

# Check if .env file exists
if (Test-Path ".env") {
    Write-Host "✓ .env file found" -ForegroundColor Green
    Write-Host "  This file will NOT be uploaded (it's in .gitignore)" -ForegroundColor Gray
} else {
    Write-Host "⚠ .env file not found (this is OK if you don't have one yet)" -ForegroundColor Yellow
}

# Check if .gitignore exists
if (Test-Path ".gitignore") {
    Write-Host "✓ .gitignore file exists" -ForegroundColor Green

    # Verify critical patterns are in .gitignore
    $gitignoreContent = Get-Content ".gitignore" -Raw
    $criticalPatterns = @(".env", "*.sql", "backups/", "data/", "logs/")
    $allPatterns = $true

    foreach ($pattern in $criticalPatterns) {
        if ($gitignoreContent -match [regex]::Escape($pattern)) {
            Write-Host "  ✓ Excludes: $pattern" -ForegroundColor Gray
        } else {
            Write-Host "  ✗ Missing: $pattern" -ForegroundColor Red
            $allPatterns = $false
        }
    }

    if (-not $allPatterns) {
        Write-Host ""
        Write-Host "ERROR: .gitignore is missing critical exclusions!" -ForegroundColor Red
        Write-Host "Please ensure sensitive files are excluded before continuing."
        exit 1
    }
} else {
    Write-Host "✗ .gitignore file missing!" -ForegroundColor Red
    Write-Host "This is required to prevent uploading sensitive data."
    exit 1
}

Write-Host ""
Write-Host "All security checks passed!" -ForegroundColor Green

# Check if already a git repository
if (Test-Path ".git") {
    Write-Host ""
    Write-Host "⚠ This is already a git repository" -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "Do you want to continue? This will change the remote to your new GitHub repo (yes/no)"
    if ($response -ne "yes" -and $response -ne "y") {
        Write-Host "Cancelled."
        exit 0
    }
} else {
    Write-Host ""
    Write-Host "Initializing git repository..." -ForegroundColor Cyan
    git init
    Write-Host "✓ Git repository initialized" -ForegroundColor Green
}

# Configure git user (if not already set)
Write-Host ""
Write-Host "Checking git configuration..." -ForegroundColor Cyan

$gitUserName = git config user.name 2>$null
$gitUserEmail = git config user.email 2>$null

if (-not $gitUserName) {
    Write-Host "Git user name not set."
    $userName = Read-Host "Enter your name (e.g., 'John Smith')"
    git config user.name "$userName"
    Write-Host "✓ User name set: $userName" -ForegroundColor Green
} else {
    Write-Host "✓ User name: $gitUserName" -ForegroundColor Green
}

if (-not $gitUserEmail) {
    Write-Host "Git user email not set."
    $userEmail = Read-Host "Enter your email"
    git config user.email "$userEmail"
    Write-Host "✓ User email set: $userEmail" -ForegroundColor Green
} else {
    Write-Host "✓ User email: $gitUserEmail" -ForegroundColor Green
}

# Show what will be committed
Write-Host ""
Write-Host "Files that will be uploaded to GitHub:" -ForegroundColor Cyan
Write-Host ""

$stagedFiles = git ls-files 2>$null
if ($stagedFiles) {
    Write-Host "Already tracked files: $($stagedFiles.Count)" -ForegroundColor Gray
}

# Add all files (respecting .gitignore)
git add -A

$statusOutput = git status --short
if ($statusOutput) {
    Write-Host ""
    Write-Host "New/Modified files to commit:" -ForegroundColor Yellow
    $statusOutput | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

    # Count files
    $fileCount = ($statusOutput | Measure-Object).Count
    Write-Host ""
    Write-Host "Total files to commit: $fileCount" -ForegroundColor Cyan
} else {
    Write-Host "No changes to commit." -ForegroundColor Yellow
}

# Safety check - ensure .env is NOT in the staging area
$stagedEnv = git diff --cached --name-only | Select-String -Pattern "\.env"
if ($stagedEnv) {
    Write-Host ""
    Write-Host "ERROR: .env file is staged for commit!" -ForegroundColor Red
    Write-Host "This contains your API keys and passwords!"
    Write-Host ""
    Write-Host "Unstaging .env file..."
    git reset HEAD .env 2>$null
    Write-Host "Please check your .gitignore file."
    exit 1
}

# Create initial commit
Write-Host ""
$response = Read-Host "Create initial commit? (yes/no)"
if ($response -eq "yes" -or $response -eq "y") {
    $commitMessage = "Initial commit: GEX Collector with Docker deployment and PostgreSQL support"
    git commit -m "$commitMessage"
    Write-Host "✓ Commit created" -ForegroundColor Green
} else {
    Write-Host "Skipping commit."
}

# GitHub repository setup
Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "GITHUB REPOSITORY SETUP" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Now you need to create a PRIVATE repository on GitHub:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Go to: https://github.com/new" -ForegroundColor White
Write-Host "2. Repository name: gextr" -ForegroundColor White
Write-Host "3. Description: SPX GEX (Gamma Exposure) collector and analysis system" -ForegroundColor White
Write-Host "4. IMPORTANT: Select 'Private' (NOT public!)" -ForegroundColor Red
Write-Host "5. DO NOT initialize with README, .gitignore, or license" -ForegroundColor White
Write-Host "6. Click 'Create repository'" -ForegroundColor White
Write-Host ""

$response = Read-Host "Have you created the private repository on GitHub? (yes/no)"
if ($response -ne "yes" -and $response -ne "y") {
    Write-Host ""
    Write-Host "Please create the repository first, then run this script again."
    exit 0
}

# Get repository URL
Write-Host ""
Write-Host "What is your GitHub repository URL?" -ForegroundColor Cyan
Write-Host "Examples:" -ForegroundColor Gray
Write-Host "  - https://github.com/johnsondatascience/gextr.git" -ForegroundColor Gray
Write-Host "  - git@github.com:johnsondatascience/gextr.git (SSH)" -ForegroundColor Gray
Write-Host ""

$repoUrl = Read-Host "Repository URL"

if (-not $repoUrl) {
    Write-Host "Error: Repository URL is required"
    exit 1
}

# Add remote
Write-Host ""
Write-Host "Adding GitHub remote..." -ForegroundColor Cyan

try {
    # Remove existing origin if present
    git remote remove origin 2>$null

    # Add new origin
    git remote add origin $repoUrl
    Write-Host "✓ Remote added: origin -> $repoUrl" -ForegroundColor Green
} catch {
    Write-Host "Note: Remote may already exist" -ForegroundColor Yellow
}

# Rename branch to main (GitHub default)
Write-Host ""
Write-Host "Setting default branch to 'main'..." -ForegroundColor Cyan
$currentBranch = git branch --show-current
if ($currentBranch -ne "main") {
    git branch -M main
    Write-Host "✓ Branch renamed to 'main'" -ForegroundColor Green
} else {
    Write-Host "✓ Already on 'main' branch" -ForegroundColor Green
}

# Push to GitHub
Write-Host ""
Write-Host "Ready to push to GitHub!" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will upload your code to: $repoUrl" -ForegroundColor White
Write-Host ""

$response = Read-Host "Push to GitHub now? (yes/no)"
if ($response -eq "yes" -or $response -eq "y") {
    Write-Host ""
    Write-Host "Pushing to GitHub..." -ForegroundColor Cyan
    Write-Host "(You may be prompted for your GitHub username and password/token)" -ForegroundColor Gray
    Write-Host ""

    try {
        git push -u origin main
        Write-Host ""
        Write-Host "==================================" -ForegroundColor Green
        Write-Host "SUCCESS!" -ForegroundColor Green
        Write-Host "==================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Your GEX collector is now on GitHub!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Repository URL:" -ForegroundColor Cyan
        Write-Host "  $repoUrl" -ForegroundColor White
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "  1. Verify repository is PRIVATE: https://github.com/johnsondatascience/gextr/settings"
        Write-Host "  2. Update migration scripts if needed (change repo URLs)"
        Write-Host "  3. Consider enabling branch protection on main branch"
        Write-Host ""
    } catch {
        Write-Host ""
        Write-Host "Error pushing to GitHub:" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        Write-Host ""
        Write-Host "Common issues:" -ForegroundColor Yellow
        Write-Host "  - Wrong credentials (need Personal Access Token, not password)"
        Write-Host "  - Repository doesn't exist"
        Write-Host "  - Repository is not empty (shouldn't initialize with README)"
        Write-Host ""
        Write-Host "To create a Personal Access Token:" -ForegroundColor Cyan
        Write-Host "  1. Go to: https://github.com/settings/tokens"
        Write-Host "  2. Click 'Generate new token (classic)'"
        Write-Host "  3. Select scopes: 'repo' (all)"
        Write-Host "  4. Generate token and save it"
        Write-Host "  5. Use token as password when prompted"
        Write-Host ""
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "Push cancelled." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "You can push manually later with:"
    Write-Host "  git push -u origin main"
    Write-Host ""
}

# Final security reminder
Write-Host ""
Write-Host "SECURITY REMINDERS:" -ForegroundColor Yellow
Write-Host "  ✓ Repository is PRIVATE (verify in GitHub settings)"
Write-Host "  ✓ .env file NOT uploaded (contains API keys)"
Write-Host "  ✓ Database backups NOT uploaded"
Write-Host "  ✓ Logs NOT uploaded"
Write-Host ""
Write-Host "To verify nothing sensitive was uploaded:"
Write-Host "  Visit: https://github.com/johnsondatascience/gextr"
Write-Host "  Check: No .env file, no *.sql files visible"
Write-Host ""
