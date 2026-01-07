# SC4S Package Tree Map - Quick Start Guide

This guide will get you up and running in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- GitHub account (for creating a Personal Access Token)

## Installation

### 1. Set up Virtual Environment

```bash
# Navigate to project directory
cd sc4s_package_tree_map

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- PyGithub (GitHub API client)
- pyparsing (Configuration parser)
- click (CLI framework)
- rich (Beautiful terminal output)
- PyYAML (Configuration files)

### 3. Configure GitHub Token (Recommended)

Without a token, you're limited to 60 API requests/hour. With a token, you get 5000/hour.

**Create a token:**
1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name like "SC4S Parser Tree"
4. Select scope: **public_repo** (read access to public repositories)
5. Click "Generate token"
6. Copy the token (starts with `ghp_`)

**Add to environment:**
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your token
echo "GITHUB_TOKEN=ghp_your_token_here" > .env
```

## Usage

### Scrape and Parse SC4S Repository

Run the scraper to download and parse all SC4S parsers:

```bash
python -m src.cli.main scrape
```

**Expected output:**
```
Initializing GitHub client...
Rate limit: 5000/5000 remaining
Loading repository: splunk/splunk-connect-for-syslog
Fetching parser files...
Found 113 files in package/etc/conf.d/conflib/syslog
...
Successfully fetched 113 parser files
Cache: 113 files, 456.2 KB

Parsing configuration files...
Parsing files... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 113/113
Parsed 150 parser definitions

Building vendor/product hierarchy...
Organized into 52 vendors

Saving output to data/parsed/sc4s_tree.json...
Successfully saved to: data/parsed/sc4s_tree.json

Summary:
  Vendors: 52
  Products: 98
  Parsers: 150
  Files processed: 113
```

This process:
1. **Downloads** 110+ configuration files from GitHub
2. **Caches** them locally (future runs are faster!)
3. **Parses** syslog-ng syntax
4. **Extracts** metadata (index, sourcetype, vendor, product)
5. **Organizes** into vendor/product hierarchy
6. **Generates** structured JSON output

### View Statistics

Check cache and API usage:

```bash
python -m src.cli.main stats
```

**Output:**
```
Cache Statistics
  Total files: 113
  Valid files: 113
  Expired files: 0
  Total size: 456.2 KB
  Cache directory: data/cache

GitHub API Rate Limit
  Remaining: 4987/5000
```

### Explore the Output

The generated JSON file contains the complete parser tree:

```bash
# View the output file
cat data/parsed/sc4s_tree.json | head -50

# Or use jq for better formatting (if installed)
jq '.metadata' data/parsed/sc4s_tree.json
```

**Sample output structure:**
```json
{
  "metadata": {
    "scraped_at": "2026-01-06T15:30:00Z",
    "repository": "splunk/splunk-connect-for-syslog",
    "total_vendors": 52,
    "total_products": 98,
    "total_parsers": 150
  },
  "vendors": [
    {
      "name": "Cisco",
      "products": [
        {
          "name": "ASA",
          "parsers": [
            {
              "name": "app-syslog-cisco_asa",
              "type": "syslog",
              "metadata": {
                "index": "netops",
                "sourcetype": "cisco:asa:syslog",
                "vendor": "cisco",
                "product": "asa"
              },
              "applications": [...]
            }
          ]
        }
      ]
    }
  ]
}
```

### Serve Web UI (Preview)

Start the web server to view the visualization:

```bash
python -m src.cli.main serve --port 8080
```

Then open http://localhost:8080 in your browser.

**Note:** The interactive visualization (D3.js tree) is in Phase 4 (upcoming). Currently shows a status page.

## Common Tasks

### Force Refresh Cache

If you want to re-download everything:

```bash
python -m src.cli.main scrape --force-refresh
```

### Clear Cache

Remove all cached files:

```bash
python -m src.cli.main clear-cache
```

### Custom Output Location

Save to a different file:

```bash
python -m src.cli.main scrape --output my_output.json
```

## Understanding the Data

### What Gets Extracted?

For each parser, the system extracts:

1. **Basic Info:**
   - Parser name (e.g., `app-syslog-cisco_asa`)
   - Parser type (syslog, json, cef, leef)
   - File path in repository

2. **Metadata:**
   - Index (where events go)
   - Sourcetype (event classification)
   - Vendor and Product
   - Template (formatting)

3. **Filters:**
   - How messages are matched
   - Filter types (program, message, host)
   - Match patterns and flags

4. **Applications:**
   - Application name and type
   - Filter expressions
   - Parser references

5. **Conditional Logic:**
   - If/elif/else rewrites
   - Dynamic routing based on content

### Example Parser

**File:** `package/etc/conf.d/conflib/syslog/app-syslog-cisco_asa.conf`

**Extracted data:**
```json
{
  "name": "app-syslog-cisco_asa",
  "type": "syslog",
  "file_path": "package/etc/conf.d/conflib/syslog/app-syslog-cisco_asa.conf",
  "metadata": {
    "index": "netops",
    "sourcetype": "cisco:asa:syslog",
    "vendor": "cisco",
    "product": "asa"
  },
  "applications": [
    {
      "name": "app-syslog-cisco_asa",
      "type": "sc4s-syslog",
      "filters": [
        {
          "type": "program",
          "pattern": "cisco_asa",
          "match_type": "string",
          "flags": ["prefix"]
        }
      ]
    }
  ]
}
```

## Troubleshooting

### Rate Limit Errors

**Problem:** `RateLimitExceededException`

**Solution:** Add a GitHub token to your `.env` file (see step 3 above)

### Import Errors

**Problem:** `ModuleNotFoundError`

**Solution:**
```bash
# Make sure you're in the project directory
pwd  # Should show: .../sc4s_package_tree_map

# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Parsing Errors

**Problem:** Some parsers fail to parse

**Expected behavior:** The system will continue and report errors at the end. SC4S has complex configuration files, and some edge cases may not parse perfectly. The system will still extract what it can.

## Next Steps

1. **Explore the data:** Open `data/parsed/sc4s_tree.json` and browse the structure
2. **Query with jq:** Use jq to filter and analyze the data
   ```bash
   # List all vendors
   jq '.vendors[].name' data/parsed/sc4s_tree.json

   # Find all Cisco products
   jq '.vendors[] | select(.name=="Cisco") | .products[].name' data/parsed/sc4s_tree.json

   # Count parsers by type
   jq '[.vendors[].products[].parsers[].type] | group_by(.) | map({type: .[0], count: length})' data/parsed/sc4s_tree.json
   ```
3. **Wait for Phase 4:** The interactive D3.js visualization is coming soon!

## Getting Help

- Check the main [README.md](README.md) for detailed documentation
- Review the implementation plan at `.claude/plans/`
- Open an issue on GitHub (if this becomes a public repo)

---

**Congratulations!** You now have a complete map of SC4S parsers with metadata, filters, and vendor/product hierarchy!
