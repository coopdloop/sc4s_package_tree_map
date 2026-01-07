# SC4S Package Tree Map

A Python-based tool that scrapes the [Splunk Connect for Syslog (SC4S)](https://github.com/splunk/splunk-connect-for-syslog) repository and generates an interactive web-based visualization showing how events flow through parsers, filters, and metadata assignments.

## Features

- **GitHub API Integration**: Fetch 110+ parser configurations from the SC4S repository
- **Intelligent Caching**: Avoid rate limits with local file caching
- **Interactive Visualization**: Explore parsers in a collapsible tree view
- **Search & Filter**: Find parsers by vendor, product, sourcetype, or index
- **Parsing Flow Analysis**: See how events are matched, parsed, and routed

## Project Status

### Phase 1: Foundation & Scraping ✅ Complete
- [x] Project structure initialized
- [x] GitHub API client with rate limiting
- [x] File fetcher with caching
- [x] Data models defined
- [x] CLI interface implemented
- [x] Configuration system

### Phase 2: Parser Development ✅ Complete
- [x] Syslog-ng configuration parser
- [x] Metadata extraction (r_set_splunk_dest_default)
- [x] Filter parsing (program, message, host)
- [x] Conditional rewrite handling (if/elif/else)
- [x] Block parser extraction
- [x] Application parser extraction
- [x] Vendor/product hierarchy builder
- [x] JSON output generation

### Phase 3: Data Analysis & Hierarchy ✅ Complete
- [x] Vendor/product extraction from parser names
- [x] Hierarchy builder (Vendor → Product → Parser tree)
- [x] Metadata aggregation
- [x] JSON output with full structure

### Phase 4: Web Visualization ✅ Complete
- [x] D3.js interactive tree visualization
- [x] Collapsible tree nodes with expand/collapse
- [x] Detail panel showing parser information
- [x] Fuzzy search with Fuse.js
- [x] Multiple view modes (vendor, type, index)
- [x] Responsive design
- [x] Click to view parser details
- [x] Zoom and pan functionality

### Phase 5: Polish & Documentation 📋 (Planned)
- [ ] Performance optimization
- [ ] Comprehensive documentation
- [ ] Demo screenshots
- [ ] Testing suite

## Quick Start

### Prerequisites

- Python 3.8 or higher
- GitHub Personal Access Token (optional but recommended)

### Installation

1. **Clone or navigate to the project directory**:
```bash
cd sc4s_package_tree_map
```

2. **Create and activate a virtual environment**:
```bash
python -m venv venv

# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment** (optional but recommended):
```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your GitHub token
# Create a token at: https://github.com/settings/tokens
# Required scope: public_repo
```

Your `.env` file should look like:
```bash
GITHUB_TOKEN=ghp_your_token_here
CONFIG_FILE=config/config.yaml
```

### Basic Usage

#### 1. Scrape Parser Files

Fetch all SC4S parser configuration files from GitHub:

```bash
python -m src.cli.main scrape
```

This will:
- Connect to the GitHub API
- Download 110+ `.conf` files from the SC4S repository
- Parse syslog-ng configuration syntax
- Extract metadata (index, sourcetype, vendor, product)
- Build vendor/product hierarchy
- Generate structured JSON output in `data/parsed/sc4s_tree.json`
- Show progress and statistics

**With GitHub Token** (5000 requests/hour):
```bash
export GITHUB_TOKEN=ghp_your_token_here
python -m src.cli.main scrape
```

**Without Token** (60 requests/hour):
```bash
python -m src.cli.main scrape
# Warning will be shown about rate limits
```

#### 2. View Statistics

Check cache status and GitHub API usage:

```bash
python -m src.cli.main stats
```

Output example:
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

#### 3. Clear Cache

Remove all cached files:

```bash
python -m src.cli.main clear-cache
```

#### 4. Export to CSV (Splunk Lookup)

Export parsed data to a Splunk-compatible CSV lookup file:

```bash
python -m src.cli.main export-csv
```

**Custom paths**:
```bash
python -m src.cli.main export-csv --input data/parsed/sc4s_tree.json --output data/export/my_parsers.csv
```

**Output**: Generates `data/export/sc4s_parsers.csv` with columns:
- `parser_name` - Parser/app name
- `parser_type` - Type (syslog, json, cef, etc.)
- `vendor`, `product` - Vendor and product information
- `has_rewrites` - Boolean indicating if parser modifies metadata (true = heavier weight)
- `rewrite_count` - Number of metadata rewrites
- `index`, `sourcetype`, `template`, `class` - Metadata fields from rewrites
- `conditional_rewrites` - Count of conditional rewrites (if/elif/else)
- `filter_programs`, `filter_messages`, `filter_hosts` - Filter patterns
- `application_names`, `application_types` - Application information

**Splunk Usage**:
1. Upload CSV to Splunk: Settings → Lookups → Lookup table files → Add new
2. Create lookup definition in transforms.conf
3. Use in searches:
   ```spl
   | inputlookup sc4s_parsers.csv
   | where has_rewrites="true"
   | table parser_name vendor product index sourcetype rewrite_count
   ```

#### 5. Serve Web UI

Start the web server to view the interactive visualization:

```bash
python -m src.cli.main serve --port 8080
```

Then open http://localhost:8080 in your browser.

**Features**:
- **Interactive Tree**: Click nodes to expand/collapse vendor/product hierarchies
- **Autocomplete Search**: Type-ahead search with suggestions for vendors, products, sourcetypes, and indexes
- **Auto-Expand Tree**: Search automatically expands tree to show all matching parsers
- **Detail Panel**: Click any parser to view complete details
- **View Modes**: Switch between Vendor, Parser Type, or Index groupings
- **Layout Modes**: Tree, Radial, or Force Graph visualizations
- **CSV Export**: Download Splunk-compatible lookup file with one click
- **Zoom & Pan**: Navigate large trees easily

## Configuration

Configuration is managed through `config/config.yaml`:

```yaml
github:
  repository: "splunk/splunk-connect-for-syslog"
  branch: "main"
  base_path: "package/etc/conf.d"
  token_env: "GITHUB_TOKEN"

scraper:
  cache_dir: "data/cache"
  cache_ttl_hours: 24
  parallel_downloads: 5
  rate_limit_buffer: 10

output:
  file: "data/parsed/sc4s_tree.json"
  format: "json"
  pretty_print: true

logging:
  level: "INFO"
  file: "data/logs/scraper.log"
  console: true
```

## Project Structure

```
sc4s_package_tree_map/
├── src/
│   ├── scraper/              # GitHub API and file fetching
│   │   ├── github_client.py  # GitHub API with rate limiting
│   │   └── file_fetcher.py   # Caching logic
│   ├── parser/               # Configuration file parsing (coming soon)
│   ├── models/               # Data models
│   │   └── data_model.py     # Core data structures
│   ├── analyzer/             # Analysis tools (coming soon)
│   └── cli/                  # Command-line interface
│       └── main.py
├── web/                      # Web visualization (coming soon)
├── data/
│   ├── cache/                # Cached .conf files
│   ├── parsed/               # Parsed JSON output
│   └── logs/                 # Log files
├── config/
│   └── config.yaml           # Configuration
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Development

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

This includes:
- pytest - Testing framework
- black - Code formatter
- flake8 - Linter
- mypy - Type checker

### Running Tests (Coming Soon)

```bash
pytest tests/
```

### Code Formatting

```bash
black src/
```

## Architecture

### Data Flow

```
GitHub API → Scraper → Parser Engine → Structured JSON → Web Visualization
```

### Key Components

1. **GitHub Scraper**: Fetches .conf files with intelligent caching and rate limiting
2. **Parser Engine**: Parses syslog-ng configuration syntax (in development)
3. **Data Model**: Structured representation of vendors, products, and parsers
4. **Hierarchy Analyzer**: Builds vendor/product tree (in development)
5. **Web Visualization**: Interactive D3.js tree view (in development)

## SC4S Parser Structure

SC4S parsers follow this structure:

```
block parser app-syslog-cisco_asa() {
    channel {
        rewrite {
            r_set_splunk_dest_default(
                index("netops")
                sourcetype("cisco:asa:syslog")
                vendor("cisco")
                product("asa")
            );
        };
    };
};

application app-syslog-cisco_asa[sc4s-syslog] {
    filter {
        program("cisco_asa" type(string) flags(prefix));
    };
    parser { app-syslog-cisco_asa(); };
};
```

This tool extracts:
- Parser names and types
- Metadata (index, sourcetype, vendor, product)
- Filter patterns (how messages are matched)
- Parsing flows (filter → parser → metadata)

## Troubleshooting

### Rate Limit Errors

**Problem**: Getting rate limit errors from GitHub

**Solution**:
1. Create a GitHub Personal Access Token
2. Add it to your `.env` file as `GITHUB_TOKEN=ghp_...`
3. This increases your limit from 60 to 5000 requests/hour

### Cache Issues

**Problem**: Cache contains stale data

**Solution**:
```bash
python -m src.cli.main clear-cache
python -m src.cli.main scrape --force-refresh
```

### Import Errors

**Problem**: `ModuleNotFoundError` when running CLI

**Solution**:
```bash
# Make sure you're in the project root directory
cd sc4s_package_tree_map

# Make sure virtual environment is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Contributing

This project is currently in active development. Phase 1 (Foundation & Scraping) is complete.

### Next Steps

To contribute to Phase 2 (Parser Development):

1. Implement `src/parser/syslog_ng_parser.py` - Main parser for syslog-ng syntax
2. Implement `src/parser/rewrite_parser.py` - Extract metadata from r_set_splunk_dest_default()
3. Implement `src/parser/filter_parser.py` - Parse filter expressions
4. Add unit tests with sample .conf files

## Resources

- [SC4S Documentation](https://splunk.github.io/splunk-connect-for-syslog/)
- [SC4S GitHub Repository](https://github.com/splunk/splunk-connect-for-syslog)
- [syslog-ng Configuration Guide](https://www.syslog-ng.com/technical-documents/doc/syslog-ng-open-source-edition/3.38/administration-guide/)

## License

This project is a development tool for analyzing SC4S configurations. SC4S itself is maintained by Splunk.

## Roadmap

- [x] Phase 1: Foundation & Scraping ✅
- [x] Phase 2: Parser Development ✅
- [x] Phase 3: Data Analysis & Hierarchy ✅
- [x] Phase 4: Web Visualization ✅
- [ ] Phase 5: Polish & Documentation (Optional enhancements)

---

**Current Status**: All Phases Complete! ✅ 🎉

The project is fully functional! The system successfully:
- ✅ Scrapes 110+ parser files from SC4S repository
- ✅ Parses syslog-ng configuration syntax
- ✅ Extracts metadata and filter patterns
- ✅ Builds vendor/product hierarchy
- ✅ Generates structured JSON output
- ✅ Interactive D3.js tree visualization
- ✅ Search and filter functionality
- ✅ Multiple view modes
- ✅ Detailed parser information panel

**Ready to use!** Follow the Quick Start guide below to get started.
