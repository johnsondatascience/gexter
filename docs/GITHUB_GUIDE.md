# GitHub Setup and Usage Guide

## Quick Setup (First Time)

### Step 1: Run the Setup Script

```powershell
cd c:\Users\johnsnmi\gextr
.\scripts\setup_github.ps1
```

The script will:
- ✓ Verify git is installed
- ✓ Check .gitignore excludes sensitive files
- ✓ Initialize git repository
- ✓ Configure your name/email
- ✓ Create initial commit
- ✓ Guide you through GitHub repository creation
- ✓ Push to GitHub

### Step 2: Create GitHub Repository

1. **Go to**: https://github.com/new
2. **Repository name**: `gextr`
3. **Description**: `SPX GEX (Gamma Exposure) collector and analysis system`
4. **IMPORTANT**: Select **Private** ⚠️
5. **DO NOT** initialize with README, .gitignore, or license
6. Click **Create repository**

### Step 3: Get Your Personal Access Token

Since GitHub no longer accepts passwords, you need a Personal Access Token:

1. Go to: https://github.com/settings/tokens
2. Click: **Generate new token (classic)**
3. Note: `GEX Collector Access`
4. Expiration: `90 days` (or your preference)
5. Select scopes: Check **`repo`** (all repo permissions)
6. Click: **Generate token**
7. **COPY THE TOKEN** - you won't see it again!
8. Use this token as your password when pushing to GitHub

---

## Security Verification

After uploading, verify these files are **NOT** visible on GitHub:

### ❌ Must NOT be uploaded:
- `.env` (contains API keys and passwords!)
- `backups/` directory (database dumps)
- `*.sql` files (database backups)
- `data/` directory (large database files)
- `logs/` directory (log files)
- `postgres_data/` (Docker volumes)
- `pgadmin_data/` (Docker volumes)

### ✓ Should be uploaded:
- All `.py` source files
- `docker-compose.yml`
- `Dockerfile`
- `requirements.txt`
- `README.md`
- `scripts/` directory
- `.gitignore` file itself

### Verify on GitHub:
Visit: https://github.com/johnsondatascience/gextr

Click through the files and ensure:
1. No `.env` file visible
2. No `backups/` folder
3. No `.sql` files
4. Repository shows **Private** badge

---

## Daily Git Workflow

### Making Changes

```powershell
cd c:\Users\johnsnmi\gextr

# 1. Check what changed
git status

# 2. See detailed changes
git diff

# 3. Add changes
git add .

# 4. Commit with message
git commit -m "Add feature: real-time GEX alerts"

# 5. Push to GitHub
git push
```

### Viewing History

```powershell
# View recent commits
git log --oneline -10

# View changes in a specific file
git log -p src/gex_collector.py

# View who changed what
git blame src/gex_collector.py
```

### Undoing Changes

```powershell
# Undo changes to a file (before commit)
git checkout -- filename.py

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes) - DANGEROUS!
git reset --hard HEAD~1
```

---

## Cloning to Another Machine

When you want to work from another computer (or your cloud VM):

```bash
# Clone the repository
git clone https://github.com/johnsondatascience/gextr.git
cd gextr

# Create .env file (not in git!)
nano .env
# Paste your configuration
# Save and exit

# Start containers
docker compose up -d
```

**IMPORTANT**: You must manually create the `.env` file after cloning since it's not in git!

---

## Branch Strategy (Future)

For now, working directly on `main` is fine. When you want to experiment:

```powershell
# Create a new branch for experimentation
git checkout -b feature/new-signals

# Make changes and commit
git add .
git commit -m "Experiment with new signal calculation"
git push -u origin feature/new-signals

# Switch back to main
git checkout main

# If experiment worked, merge it
git merge feature/new-signals
git push

# Delete the branch
git branch -d feature/new-signals
git push origin --delete feature/new-signals
```

---

## Common Issues & Solutions

### Issue: "Authentication failed"

**Solution**: You need a Personal Access Token, not your GitHub password.
1. Go to: https://github.com/settings/tokens
2. Generate new token (classic) with `repo` scope
3. Use token as password when git prompts

### Issue: "Repository not found"

**Solutions**:
1. Verify repository exists: https://github.com/johnsondatascience/gextr
2. Check remote URL: `git remote -v`
3. Fix if wrong: `git remote set-url origin https://github.com/johnsondatascience/gextr.git`

### Issue: ".env file was committed!"

**Emergency fix**:
```powershell
# Remove from git but keep local file
git rm --cached .env
git commit -m "Remove .env from git"
git push

# Verify .env is in .gitignore
cat .gitignore | findstr ".env"
```

**Then rotate your API keys immediately**:
1. Get new Tradier API key: https://documentation.tradier.com/getting-started
2. Change PostgreSQL passwords
3. Update `.env` with new credentials

### Issue: "Push rejected - diverged histories"

**Solution**:
```powershell
# Pull changes first
git pull origin main

# If conflicts, resolve them
# Then push
git push
```

---

## GitHub Features to Use

### 1. Releases

When you reach milestones (e.g., 6 months of data, validated strategy):

1. Go to: https://github.com/johnsondatascience/gextr/releases
2. Click: **Draft a new release**
3. Tag: `v1.0.0` (follow semantic versioning)
4. Title: `GEX Collector v1.0 - Production Ready`
5. Description: What's included, major features
6. Publish release

### 2. Issues

Track bugs and features:

1. Go to: https://github.com/johnsondatascience/gextr/issues
2. Click: **New issue**
3. Title: `Add 0DTE-specific GEX calculation`
4. Description: Details, acceptance criteria
5. Assign to yourself
6. Add labels: `enhancement`, `priority: high`

### 3. Projects (Kanban Board)

Organize your work:

1. Go to: https://github.com/johnsondatascience/gextr/projects
2. Create project: `GEX Collector Development`
3. Create columns: `To Do`, `In Progress`, `Done`
4. Add cards for features/bugs

---

## Backing Up to GitHub

### Daily Backup Workflow

```powershell
# At end of coding session
git add .
git commit -m "Daily update: $(Get-Date -Format 'yyyy-MM-dd')"
git push
```

### Before Major Changes

```powershell
# Create a backup branch
git checkout -b backup/before-major-refactor
git push -u origin backup/before-major-refactor

# Go back to main and make changes
git checkout main
# ... make changes ...
```

---

## Collaboration (Future)

When bringing in collaborators or investors who want to see code:

### Inviting Collaborators

1. Go to: https://github.com/johnsondatascience/gextr/settings/access
2. Click: **Invite a collaborator**
3. Enter their GitHub username
4. Choose permission level:
   - **Read**: Can view code only
   - **Write**: Can push changes
   - **Admin**: Full access

### Code Reviews

When getting feedback:
1. Push your branch: `git push origin feature/new-calculation`
2. Create Pull Request on GitHub
3. Request review from collaborator
4. Address feedback
5. Merge when approved

---

## Useful Git Commands Reference

```powershell
# Status and info
git status                  # What changed
git log                     # Commit history
git diff                    # See changes
git branch                  # List branches
git remote -v              # Show remote URLs

# Making changes
git add <file>             # Stage specific file
git add .                  # Stage all changes
git commit -m "message"    # Commit staged changes
git push                   # Push to GitHub

# Branches
git branch <name>          # Create branch
git checkout <name>        # Switch branch
git checkout -b <name>     # Create and switch
git merge <name>           # Merge branch into current
git branch -d <name>       # Delete branch

# Syncing
git pull                   # Fetch and merge from GitHub
git fetch                  # Fetch without merging
git push                   # Push commits to GitHub

# Undoing
git checkout -- <file>     # Discard changes to file
git reset HEAD <file>      # Unstage file
git reset --soft HEAD~1    # Undo last commit, keep changes
git reset --hard HEAD~1    # Undo last commit, discard changes

# Viewing
git show <commit>          # Show commit details
git blame <file>           # Who changed what
git log --oneline          # Condensed history
```

---

## Migration Scripts Update

After uploading to GitHub, update your migration scripts to use the GitHub URL:

In `scripts/migration/01_setup_vm.sh`:
```bash
# Instead of copying scripts manually, can clone from GitHub:
git clone https://github.com/johnsondatascience/gextr.git /home/gex/gextr
```

This makes VM setup even easier!

---

## Security Checklist

Before each push, verify:

- [ ] `.env` file is NOT staged (`git status` should not show .env)
- [ ] No `*.sql` files staged
- [ ] No database backups staged
- [ ] No sensitive credentials in code
- [ ] Repository is set to **Private**
- [ ] Personal Access Token is secure (not committed anywhere!)

---

## Next Steps

After setting up GitHub:

1. **Verify privacy**: Check repository is private
2. **Test clone**: Clone to a different folder to ensure it works
3. **Update documentation**: Add GitHub URLs where relevant
4. **Set up branch protection** (optional): Prevent force pushes to main
5. **Create first release**: Tag initial working version

---

## Resources

- **GitHub Docs**: https://docs.github.com
- **Git Cheat Sheet**: https://training.github.com/downloads/github-git-cheat-sheet.pdf
- **Personal Access Tokens**: https://github.com/settings/tokens
- **Your Repository**: https://github.com/johnsondatascience/gextr

---

**Remember**: The repository is your backup and collaboration hub. Commit often, push daily!
