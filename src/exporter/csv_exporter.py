"""
CSV Exporter for SC4S parser data - Splunk lookup compatible.
"""
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..models.data_model import SC4STreeData, ParserDefinition


class CSVExporter:
    """Export SC4S parser data to CSV format for Splunk lookups."""

    # CSV column headers
    HEADERS = [
        'parser_name',
        'parser_type',
        'vendor',
        'product',
        'file_path',
        'has_rewrites',
        'rewrite_count',
        'index',
        'sourcetype',
        'template',
        'class',
        'conditional_rewrites',
        'filter_programs',
        'filter_messages',
        'filter_hosts',
        'application_names',
        'application_types'
    ]

    @staticmethod
    def export_to_csv(tree_data: SC4STreeData, output_path: str) -> Dict[str, Any]:
        """
        Export SC4S tree data to CSV file.

        Args:
            tree_data: SC4STreeData object containing parsed data
            output_path: Path to output CSV file

        Returns:
            Dictionary with export statistics
        """
        # Flatten parsers from hierarchical structure
        rows = CSVExporter.flatten_parsers(tree_data)

        # Ensure output directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Write CSV file
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSVExporter.HEADERS)
            writer.writeheader()
            writer.writerows(rows)

        # Calculate statistics
        stats = {
            'total_rows': len(rows),
            'parsers_with_rewrites': sum(1 for row in rows if row['has_rewrites'] == 'true'),
            'parsers_without_rewrites': sum(1 for row in rows if row['has_rewrites'] == 'false'),
            'output_file': str(output_file)
        }

        return stats

    @staticmethod
    def flatten_parsers(tree_data: SC4STreeData) -> List[Dict[str, str]]:
        """
        Flatten hierarchical parser data into list of rows.

        Args:
            tree_data: SC4STreeData object

        Returns:
            List of dictionaries, one per parser
        """
        rows = []

        for vendor in tree_data.vendors:
            for product in vendor.products:
                for parser in product.parsers:
                    row = CSVExporter.parser_to_row(parser, vendor.name, product.name)
                    rows.append(row)

        return rows

    @staticmethod
    def parser_to_row(parser: ParserDefinition, vendor: str, product: str) -> Dict[str, str]:
        """
        Convert a ParserDefinition to a CSV row dictionary.

        Args:
            parser: ParserDefinition object
            vendor: Vendor name
            product: Product name

        Returns:
            Dictionary with CSV column values
        """
        # Calculate rewrite information
        has_rewrites, rewrite_count = CSVExporter.calculate_rewrite_info(parser)

        # Extract ALL metadata values (base + conditional rewrites)
        all_metadata = CSVExporter.extract_all_metadata(parser)

        # Extract filter patterns
        filter_programs = CSVExporter.extract_filters(parser, 'program')
        filter_messages = CSVExporter.extract_filters(parser, 'message')
        filter_hosts = CSVExporter.extract_filters(parser, 'host')

        # Extract application information
        application_names = ';'.join(app.name for app in parser.applications) if parser.applications else ''
        application_types = ';'.join(app.app_type for app in parser.applications) if parser.applications else ''

        # Build row
        row = {
            'parser_name': parser.name,
            'parser_type': parser.parser_type,
            'vendor': vendor,
            'product': product,
            'file_path': parser.file_path,
            'has_rewrites': 'true' if has_rewrites else 'false',
            'rewrite_count': str(rewrite_count),
            'index': all_metadata['index'],
            'sourcetype': all_metadata['sourcetype'],
            'template': all_metadata['template'],
            'class': all_metadata['class'],
            'conditional_rewrites': str(len(parser.conditional_rewrites)),
            'filter_programs': filter_programs,
            'filter_messages': filter_messages,
            'filter_hosts': filter_hosts,
            'application_names': application_names,
            'application_types': application_types
        }

        return row

    @staticmethod
    def calculate_rewrite_info(parser: ParserDefinition) -> tuple[bool, int]:
        """
        Calculate whether parser has rewrites and count them.

        A parser has rewrites if it modifies any metadata (index, sourcetype, etc.)

        Args:
            parser: ParserDefinition object

        Returns:
            Tuple of (has_rewrites, rewrite_count)
        """
        rewrite_count = 0

        # Check base metadata
        if any([
            parser.metadata.index,
            parser.metadata.sourcetype,
            parser.metadata.vendor,
            parser.metadata.product,
            parser.metadata.template,
            parser.metadata.class_
        ]):
            rewrite_count += 1

        # Add conditional rewrites
        rewrite_count += len(parser.conditional_rewrites)

        has_rewrites = rewrite_count > 0

        return has_rewrites, rewrite_count

    @staticmethod
    def extract_all_metadata(parser: ParserDefinition) -> Dict[str, str]:
        """
        Extract all metadata values from parser (base + conditional rewrites).

        Collects all unique values for index, sourcetype, template, and class
        from both the base metadata and all conditional rewrites.

        Args:
            parser: ParserDefinition object

        Returns:
            Dictionary with semicolon-separated metadata values
        """
        indexes = set()
        sourcetypes = set()
        templates = set()
        classes = set()

        # Add base metadata
        if parser.metadata.index:
            indexes.add(parser.metadata.index)
        if parser.metadata.sourcetype:
            sourcetypes.add(parser.metadata.sourcetype)
        if parser.metadata.template:
            templates.add(parser.metadata.template)
        if parser.metadata.class_:
            classes.add(parser.metadata.class_)

        # Add metadata from conditional rewrites
        for cond_rewrite in parser.conditional_rewrites:
            if cond_rewrite.metadata.index:
                indexes.add(cond_rewrite.metadata.index)
            if cond_rewrite.metadata.sourcetype:
                sourcetypes.add(cond_rewrite.metadata.sourcetype)
            if cond_rewrite.metadata.template:
                templates.add(cond_rewrite.metadata.template)
            if cond_rewrite.metadata.class_:
                classes.add(cond_rewrite.metadata.class_)

        # Join with semicolons, sort for consistency
        return {
            'index': ';'.join(sorted(indexes)) if indexes else '',
            'sourcetype': ';'.join(sorted(sourcetypes)) if sourcetypes else '',
            'template': ';'.join(sorted(templates)) if templates else '',
            'class': ';'.join(sorted(classes)) if classes else ''
        }

    @staticmethod
    def extract_filters(parser: ParserDefinition, filter_type: str) -> str:
        """
        Extract filter patterns of a specific type from parser.

        Args:
            parser: ParserDefinition object
            filter_type: Type of filter ('program', 'message', 'host')

        Returns:
            Semicolon-separated string of filter patterns
        """
        patterns = []

        # Extract from applications
        for app in parser.applications:
            for filter_expr in app.filters:
                if filter_expr.filter_type == filter_type:
                    patterns.append(filter_expr.pattern)

        return ';'.join(patterns) if patterns else ''
