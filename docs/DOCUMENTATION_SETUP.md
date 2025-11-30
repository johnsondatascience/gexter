# Documentation Setup & Deployment Guide

This guide explains how to build, serve, and deploy the GEXter documentation.

## Overview

GEXter uses **MkDocs with Material theme** to generate beautiful, searchable documentation that can be hosted online.

## Local Development

### Prerequisites

```bash
pip install -r requirements.txt
```

This installs:
- `mkdocs` - Documentation generator
- `mkdocs-material` - Material theme
- `mkdocstrings[python]` - Auto-generate API docs from code
- `mkdocs-jupyter` - Include Jupyter notebooks in docs

### Serve Locally

To view the documentation locally with live reload:

```bash
mkdocs serve
```

Then open your browser to: **http://127.0.0.1:8000**

Any changes you make to markdown files will automatically reload in the browser!

### Build Static Site

To build the static HTML site:

```bash
mkdocs build
```

This creates a `site/` directory with all HTML, CSS, and JavaScript files.

## Project Structure

```
gexter/
├── mkdocs.yml              # MkDocs configuration
├── docs/                   # Documentation source
│   ├── index.md            # Homepage
│   ├── README.md           # Quick start (copied from root)
│   ├── api/                # API reference docs
│   │   ├── gex_collector.md
│   │   ├── database.md
│   │   └── scheduler.md
│   ├── stylesheets/        # Custom CSS
│   │   └── extra.css
│   ├── javascripts/        # Custom JavaScript
│   │   └── extra.js
│   └── *.md                # All other documentation
└── site/                   # Generated static site (after build)
```

## Configuration

The documentation is configured in [mkdocs.yml](../mkdocs.yml):

### Key Configuration Sections

**Site Information:**
```yaml
site_name: GEXter - Gamma Exposure Data Platform
site_description: Production-ready SPX option chain data collector
site_url: https://yourusername.github.io/gexter
```

**Theme (Material):**
```yaml
theme:
  name: material
  palette:
    - scheme: default  # Light mode
    - scheme: slate    # Dark mode
  features:
    - navigation.instant
    - navigation.tabs
    - search.suggest
    - content.code.copy
```

**Plugins:**
```yaml
plugins:
  - search                    # Built-in search
  - mkdocstrings              # Auto-generate API docs
  - mkdocs-jupyter            # Include notebooks
```

## Navigation Structure

The navigation menu is defined in `mkdocs.yml`:

```yaml
nav:
  - Home: index.md
  - Getting Started:
      - Quick Start: README.md
      - Deployment Guide: deployment_guide.md
  - Trading Strategies:
      - Strategy Whitepaper: STRATEGY_WHITEPAPER.md
      - Trading Signals: TRADING_SIGNALS_GUIDE.md
  - API Reference:
      - GEX Collector: api/gex_collector.md
      - Database: api/database.md
```

## Deployment Options

### Option 1: GitHub Pages (Free, Recommended)

Deploy to GitHub Pages for free hosting:

1. **Build and deploy:**
   ```bash
   mkdocs gh-deploy
   ```

2. **Configure GitHub Pages:**
   - Go to your GitHub repo settings
   - Under "Pages", select `gh-pages` branch as source
   - Your docs will be at: `https://yourusername.github.io/gexter/`

3. **Automate with GitHub Actions:**
   Create `.github/workflows/docs.yml`:
   ```yaml
   name: Deploy Documentation
   on:
     push:
       branches: [main]
   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-python@v4
           with:
             python-version: 3.x
         - run: pip install -r requirements.txt
         - run: mkdocs gh-deploy --force
   ```

### Option 2: Read the Docs (Free)

Deploy to Read the Docs:

1. **Create `.readthedocs.yaml`:**
   ```yaml
   version: 2
   build:
     os: ubuntu-22.04
     tools:
       python: "3.11"
   mkdocs:
     configuration: mkdocs.yml
   python:
     install:
       - requirements: requirements.txt
   ```

2. **Connect your GitHub repo:**
   - Go to [readthedocs.org](https://readthedocs.org)
   - Import your GitHub repository
   - Docs will auto-build on each push

3. **Your docs will be at:**
   `https://gexter.readthedocs.io`

### Option 3: Netlify (Free)

Deploy to Netlify:

1. **Create `netlify.toml`:**
   ```toml
   [build]
   command = "mkdocs build"
   publish = "site"

   [build.environment]
   PYTHON_VERSION = "3.11"
   ```

2. **Deploy:**
   - Connect your GitHub repo to Netlify
   - Set build command: `mkdocs build`
   - Set publish directory: `site`

3. **Automatic deploys:**
   - Every push to `main` triggers a rebuild

### Option 4: Self-Hosted

Host on your own server:

1. **Build the site:**
   ```bash
   mkdocs build
   ```

2. **Copy to web server:**
   ```bash
   scp -r site/* user@yourserver:/var/www/html/docs/
   ```

3. **Nginx configuration:**
   ```nginx
   server {
       listen 80;
       server_name docs.yoursite.com;
       root /var/www/html/docs;
       index index.html;

       location / {
           try_files $uri $uri/ =404;
       }
   }
   ```

## Customization

### Custom Styling

Add custom CSS in [docs/stylesheets/extra.css](stylesheets/extra.css):

```css
/* Custom styles */
.md-header {
  background-color: #2196f3;
}
```

### Custom JavaScript

Add custom JS in [docs/javascripts/extra.js](javascripts/extra.js):

```javascript
// Custom functionality
document.addEventListener('DOMContentLoaded', function() {
  // Your code here
});
```

### Code Documentation

The `mkdocstrings` plugin auto-generates API docs from Python docstrings:

```markdown
# In any .md file:
::: src.gex_collector
```

This will automatically include:
- Function signatures
- Docstrings
- Type annotations
- Source code (optional)

### Jupyter Notebooks

Include notebooks directly in documentation:

```markdown
# In any .md file:
!jupyter:docs/investor_charts.ipynb
```

The notebook will be rendered inline with syntax highlighting.

## Tips & Best Practices

### 1. Live Reload During Development

Always use `mkdocs serve` while editing docs to see changes in real-time.

### 2. Check for Broken Links

MkDocs warns about broken links during build. Pay attention to warnings:

```
WARNING - Doc file 'index.md' contains a link 'broken.md', but the target is not found
```

### 3. Use Admonitions

Highlight important information:

```markdown
!!! note
    This is a note

!!! warning
    This is a warning

!!! tip
    This is a helpful tip
```

### 4. Code Blocks with Syntax Highlighting

```markdown
\`\`\`python
def example():
    return "Hello, World!"
\`\`\`
```

### 5. Mermaid Diagrams

Create diagrams in markdown:

```markdown
\`\`\`mermaid
graph LR
    A[Start] --> B[Process]
    B --> C[End]
\`\`\`
```

### 6. Search Optimization

- Use descriptive headings
- Include relevant keywords
- Write clear summaries
- The search plugin indexes everything automatically

## Updating Documentation

### Daily Workflow

1. **Edit markdown files** in `docs/`
2. **Preview changes:** `mkdocs serve`
3. **Commit changes:** `git add docs/ && git commit -m "Update docs"`
4. **Push:** `git push`
5. **Auto-deploy** (if configured)

### Adding New Pages

1. **Create new `.md` file** in `docs/`
2. **Add to navigation** in `mkdocs.yml`:
   ```yaml
   nav:
     - New Section:
         - My New Page: new_page.md
   ```
3. **Build and preview**

### Updating API Docs

API documentation auto-generates from code:

1. **Write good docstrings** in Python code:
   ```python
   def my_function(param: str) -> bool:
       """
       Short description.

       Args:
           param: Description of parameter

       Returns:
           Description of return value
       """
   ```

2. **Reference in docs:**
   ```markdown
   ::: src.module_name.my_function
   ```

## Troubleshooting

### Build Errors

```bash
# Clean and rebuild
mkdocs build --clean
```

### Port Already in Use

```bash
# Use different port
mkdocs serve -a 127.0.0.1:8001
```

### Missing Dependencies

```bash
# Reinstall all requirements
pip install -r requirements.txt --force-reinstall
```

### Broken Links

Check warnings during build and fix referenced files.

## Resources

- **MkDocs Documentation:** https://www.mkdocs.org
- **Material Theme:** https://squidfunk.github.io/mkdocs-material/
- **MkDocstrings:** https://mkdocstrings.github.io
- **Markdown Guide:** https://www.markdownguide.org

## Quick Reference

```bash
# Serve locally with live reload
mkdocs serve

# Build static site
mkdocs build

# Deploy to GitHub Pages
mkdocs gh-deploy

# Build with clean slate
mkdocs build --clean

# Serve on different port
mkdocs serve -a 127.0.0.1:8001

# Show MkDocs version
mkdocs --version
```

---

**Next Steps:**
1. Customize the [mkdocs.yml](../mkdocs.yml) with your information
2. Deploy to GitHub Pages or Read the Docs
3. Share your documentation URL with users!
