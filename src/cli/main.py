"""
CLI interface for SC4S Parser Tree Map.
"""
import os
import sys
import json
import logging
import http.server
import socketserver
from pathlib import Path
from typing import Optional

import click
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import track

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scraper.github_client import GitHubClient
from src.scraper.file_fetcher import FileFetcher
from src.models.data_model import SC4STreeData
from src.models.graph import GraphBuilder
from src.parser.syslog_ng_parser import SyslogNgParser
from src.analyzer.hierarchy_builder import HierarchyBuilder
from src.exporter.csv_exporter import CSVExporter

console = Console()


def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """Setup logging configuration."""
    handlers = [RichHandler(console=console, rich_tracebacks=True)]

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers
    )


def load_config(config_file: str) -> dict:
    """Load configuration from YAML file."""
    config_path = Path(config_file)
    if not config_path.exists():
        console.print(f"[red]Config file not found: {config_file}[/red]")
        sys.exit(1)

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


@click.group()
@click.option('--config', default='config/config.yaml', help='Path to config file')
@click.pass_context
def cli(ctx, config):
    """SC4S Parser Tree Map - Scrape and visualize SC4S parsers."""
    # Load environment variables
    load_dotenv()

    # Load config
    ctx.ensure_object(dict)
    ctx.obj['config'] = load_config(config)

    # Setup logging
    log_config = ctx.obj['config'].get('logging', {})
    setup_logging(
        level=log_config.get('level', 'INFO'),
        log_file=log_config.get('file')
    )


@cli.command()
@click.option('--output', '-o', help='Output file path')
@click.option('--force-refresh', is_flag=True, help='Force refresh cache')
@click.pass_context
def scrape(ctx, output, force_refresh):
    """Scrape SC4S parsers from GitHub and generate JSON output."""
    config = ctx.obj['config']

    # Get GitHub token
    token_env = config['github'].get('token_env', 'GITHUB_TOKEN')
    token = os.getenv(token_env)

    if not token:
        console.print(f"[yellow]Warning: No GitHub token found in ${token_env}[/yellow]")
        console.print("[yellow]Running unauthenticated (60 requests/hour limit)[/yellow]")
        console.print("[yellow]Create a token at: https://github.com/settings/tokens[/yellow]")

    # Initialize clients
    console.print("[bold blue]Initializing GitHub client...[/bold blue]")
    client = GitHubClient(
        token=token,
        rate_limit_buffer=config['scraper'].get('rate_limit_buffer', 10)
    )

    fetcher = FileFetcher(
        client=client,
        cache_dir=config['scraper']['cache_dir'],
        cache_ttl_hours=config['scraper']['cache_ttl_hours']
    )

    # Show rate limit status
    rate_status = client.get_rate_limit_status()
    console.print(f"[dim]Rate limit: {rate_status['remaining']}/{rate_status['limit']} remaining[/dim]")

    # Get repository
    repo_name = config['github']['repository']
    console.print(f"[bold blue]Loading repository: {repo_name}[/bold blue]")
    repo = client.get_repository(repo_name)

    # Fetch all parser files
    console.print("[bold blue]Fetching parser files...[/bold blue]")
    parser_files = fetcher.fetch_all_parsers(
        repo=repo,
        base_path=config['github']['base_path'],
        ref=config['github']['branch'],
        use_cache=True,
        force_refresh=force_refresh
    )

    console.print(f"[green]Successfully fetched {len(parser_files)} parser files[/green]")

    # Show cache stats
    cache_stats = fetcher.get_cache_stats()
    console.print(f"[dim]Cache: {cache_stats['valid_files']} files, "
                  f"{cache_stats['total_size_bytes'] / 1024:.1f} KB[/dim]")

    # Parse configuration files
    console.print("\n[bold blue]Parsing configuration files...[/bold blue]")
    parser = SyslogNgParser()

    extract_raw = config['parser'].get('extract_raw_config', False)

    all_parsers = []
    parse_errors = 0

    for file_path, content in track(parser_files, description="Parsing files..."):
        try:
            parsers = parser.parse_file(file_path, content, extract_raw)
            all_parsers.extend(parsers)

            # Count errors
            for p in parsers:
                if p.parse_error:
                    parse_errors += 1

        except Exception as e:
            console.print(f"[red]Error parsing {file_path}: {e}[/red]")
            parse_errors += 1

    console.print(f"[green]Parsed {len(all_parsers)} parser definitions[/green]")
    if parse_errors > 0:
        console.print(f"[yellow]Warning: {parse_errors} parsing errors[/yellow]")

    # Build hierarchy
    console.print("\n[bold blue]Building vendor/product hierarchy...[/bold blue]")
    hierarchy_builder = HierarchyBuilder()
    tree_data = hierarchy_builder.build_hierarchy(all_parsers)

    console.print(f"[green]Organized into {len(tree_data.vendors)} vendors[/green]")

    # Build graph views
    console.print("[bold blue]Building visualization graphs...[/bold blue]")
    graph_builder = GraphBuilder()

    # Build all view hierarchies
    views = graph_builder.build_all_views(tree_data)
    flat_list = graph_builder.build_flat_list(tree_data)

    # Create complete output structure
    output_data = tree_data.to_dict()
    output_data['views'] = views
    output_data['parsers_flat'] = flat_list

    # Save output
    output_file = output or config['output']['file']
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold blue]Saving output to {output_path}...[/bold blue]")

    with open(output_path, 'w') as f:
        json.dump(
            output_data,
            f,
            indent=2 if config['output']['pretty_print'] else None
        )

    console.print(f"[green]Successfully saved to: {output_path}[/green]")

    # Print summary
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Vendors: {tree_data.metadata['total_vendors']}")
    console.print(f"  Products: {tree_data.metadata['total_products']}")
    console.print(f"  Parsers: {tree_data.metadata['total_parsers']}")
    console.print(f"  Files processed: {len(parser_files)}")
    if parse_errors > 0:
        console.print(f"  Parse errors: {parse_errors}")


@cli.command()
@click.pass_context
def stats(ctx):
    """Show statistics about cached data."""
    config = ctx.obj['config']

    # Initialize fetcher to get cache stats
    token = os.getenv(config['github'].get('token_env', 'GITHUB_TOKEN'))
    client = GitHubClient(token=token)
    fetcher = FileFetcher(
        client=client,
        cache_dir=config['scraper']['cache_dir'],
        cache_ttl_hours=config['scraper']['cache_ttl_hours']
    )

    cache_stats = fetcher.get_cache_stats()

    console.print("\n[bold]Cache Statistics[/bold]")
    console.print(f"  Total files: {cache_stats['total_files']}")
    console.print(f"  Valid files: {cache_stats['valid_files']}")
    console.print(f"  Expired files: {cache_stats['expired_files']}")
    console.print(f"  Total size: {cache_stats['total_size_bytes'] / 1024:.1f} KB")
    console.print(f"  Cache directory: {cache_stats['cache_dir']}\n")

    # Show rate limit
    rate_status = client.get_rate_limit_status()
    console.print("[bold]GitHub API Rate Limit[/bold]")
    console.print(f"  Remaining: {rate_status['remaining']}/{rate_status['limit']}")


@cli.command()
@click.pass_context
def clear_cache(ctx):
    """Clear all cached files."""
    config = ctx.obj['config']

    token = os.getenv(config['github'].get('token_env', 'GITHUB_TOKEN'))
    client = GitHubClient(token=token)
    fetcher = FileFetcher(
        client=client,
        cache_dir=config['scraper']['cache_dir'],
        cache_ttl_hours=config['scraper']['cache_ttl_hours']
    )

    if click.confirm('Are you sure you want to clear the cache?'):
        fetcher.clear_cache()
        console.print("[green]Cache cleared successfully[/green]")
    else:
        console.print("[yellow]Cache clear cancelled[/yellow]")


@cli.command()
@click.option('--port', '-p', default=8080, help='Port to serve on')
@click.option('--host', '-h', default='localhost', help='Host to bind to')
@click.pass_context
def serve(ctx, port, host):
    """Serve the web visualization."""
    # Serve from project root to access both web/ and data/ directories
    project_root = Path(__file__).parent.parent.parent
    web_dir = project_root / 'web'

    if not web_dir.exists():
        console.print("[red]Web directory not found[/red]")
        sys.exit(1)

    # Check if data file exists
    data_file = project_root / 'data' / 'parsed' / 'sc4s_tree.json'
    if not data_file.exists():
        console.print("[yellow]Warning: Data file not found at data/parsed/sc4s_tree.json[/yellow]")
        console.print("[yellow]Run 'python -m src.cli.main scrape' first to generate data[/yellow]")

    os.chdir(project_root)

    class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            super().end_headers()

        def translate_path(self, path):
            """Translate URL path to filesystem path, routing / to /web/index.html"""
            # Remove query parameters
            path = path.split('?', 1)[0]
            path = path.split('#', 1)[0]

            # Redirect root to web/index.html
            if path == '/' or path == '':
                path = '/web/index.html'
            # Prefix paths that don't start with /data or /web
            elif not path.startswith('/data') and not path.startswith('/web'):
                path = '/web' + path

            # Use parent's method with modified path
            return super().translate_path(path)

    try:
        with socketserver.TCPServer((host, port), MyHTTPRequestHandler) as httpd:
            console.print(f"[bold green]Serving at http://{host}:{port}[/bold green]")
            console.print("[dim]Press Ctrl+C to stop[/dim]")
            httpd.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")
    except OSError as e:
        console.print(f"[red]Failed to start server: {e}[/red]")
        console.print(f"[yellow]Port {port} may already be in use. Try a different port with --port[/yellow]")
        sys.exit(1)


@cli.command()
@click.option('--input', '-i', help='Input JSON file path')
@click.option('--output', '-o', help='Output CSV file path')
@click.pass_context
def export_csv(ctx, input, output):
    """Export parser data to CSV for Splunk lookup."""
    config = ctx.obj['config']

    # Determine input and output paths
    input_file = input or config['output']['file']
    output_file = output or 'data/export/sc4s_parsers.csv'

    input_path = Path(input_file)
    if not input_path.exists():
        console.print(f"[red]Input file not found: {input_file}[/red]")
        console.print("[yellow]Run 'python -m src.cli.main scrape' first to generate data[/yellow]")
        sys.exit(1)

    console.print(f"[bold blue]Loading data from {input_path}...[/bold blue]")

    # Load JSON data
    with open(input_path, 'r') as f:
        data_dict = json.load(f)

    # Reconstruct SC4STreeData from dict
    # Simple reconstruction - assumes vendors list exists
    tree_data = SC4STreeData()
    tree_data.metadata = data_dict.get('metadata', {})

    # Reconstruct vendors/products/parsers from dict
    from src.models.data_model import Vendor, Product, ParserDefinition, Metadata, Application, FilterExpression, ConditionalRewrite

    for vendor_dict in data_dict.get('vendors', []):
        vendor = Vendor(name=vendor_dict['name'])

        for product_dict in vendor_dict.get('products', []):
            product = Product(name=product_dict['name'], vendor=vendor.name)

            for parser_dict in product_dict.get('parsers', []):
                # Reconstruct metadata
                metadata_dict = parser_dict.get('metadata', {})
                metadata = Metadata(
                    index=metadata_dict.get('index'),
                    sourcetype=metadata_dict.get('sourcetype'),
                    vendor=metadata_dict.get('vendor'),
                    product=metadata_dict.get('product'),
                    template=metadata_dict.get('template'),
                    class_=metadata_dict.get('class_')
                )

                # Reconstruct applications
                applications = []
                for app_dict in parser_dict.get('applications', []):
                    filters = []
                    for filter_dict in app_dict.get('filters', []):
                        filter_expr = FilterExpression(
                            filter_type=filter_dict.get('type', 'filter'),
                            pattern=filter_dict.get('pattern', ''),
                            match_type=filter_dict.get('match_type', 'string'),
                            flags=filter_dict.get('flags', []),
                            raw=filter_dict.get('raw')
                        )
                        filters.append(filter_expr)

                    app = Application(
                        name=app_dict['name'],
                        app_type=app_dict.get('type', ''),
                        filters=filters,
                        parser_reference=app_dict.get('parser_reference')
                    )
                    applications.append(app)

                # Reconstruct conditional rewrites
                conditional_rewrites = []
                for cr_dict in parser_dict.get('conditional_rewrites', []):
                    condition = None
                    if cr_dict.get('condition'):
                        cond_dict = cr_dict['condition']
                        condition = FilterExpression(
                            filter_type=cond_dict.get('type', 'filter'),
                            pattern=cond_dict.get('pattern', ''),
                            match_type=cond_dict.get('match_type', 'string'),
                            flags=cond_dict.get('flags', [])
                        )

                    metadata_cr_dict = cr_dict.get('metadata', {})
                    metadata_cr = Metadata(
                        index=metadata_cr_dict.get('index'),
                        sourcetype=metadata_cr_dict.get('sourcetype'),
                        vendor=metadata_cr_dict.get('vendor'),
                        product=metadata_cr_dict.get('product'),
                        template=metadata_cr_dict.get('template'),
                        class_=metadata_cr_dict.get('class_')
                    )

                    cr = ConditionalRewrite(
                        condition=condition,
                        metadata=metadata_cr,
                        condition_type=cr_dict.get('condition_type', 'if')
                    )
                    conditional_rewrites.append(cr)

                # Create parser
                parser = ParserDefinition(
                    name=parser_dict['name'],
                    parser_type=parser_dict.get('type', 'unknown'),
                    file_path=parser_dict.get('file_path', ''),
                    metadata=metadata,
                    applications=applications,
                    nested_parsers=parser_dict.get('nested_parsers', []),
                    conditional_rewrites=conditional_rewrites,
                    parse_error=parser_dict.get('parse_error')
                )

                product.parsers.append(parser)

            vendor.products.append(product)

        tree_data.vendors.append(vendor)

    # Export to CSV
    console.print(f"[bold blue]Exporting to CSV...[/bold blue]")

    stats = CSVExporter.export_to_csv(tree_data, output_file)

    # Display results
    console.print(f"\n[green]Successfully exported to: {stats['output_file']}[/green]")
    console.print("\n[bold]Export Statistics:[/bold]")
    console.print(f"  Total parsers: {stats['total_rows']}")
    console.print(f"  Parsers with rewrites: {stats['parsers_with_rewrites']} [green](heavier weight in Splunk)[/green]")
    console.print(f"  Parsers without rewrites: {stats['parsers_without_rewrites']}")

    console.print("\n[bold]Splunk Usage:[/bold]")
    console.print("  1. Upload CSV to Splunk as lookup: [cyan]sc4s_parsers.csv[/cyan]")
    console.print("  2. Use in searches: [cyan]| inputlookup sc4s_parsers.csv[/cyan]")
    console.print("  3. Filter by rewrites: [cyan]| inputlookup sc4s_parsers.csv | where has_rewrites=\"true\"[/cyan]")


if __name__ == '__main__':
    cli(obj={})
