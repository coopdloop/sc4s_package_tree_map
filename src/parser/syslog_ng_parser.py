"""
Main parser for syslog-ng configuration files.
"""
import logging
from typing import List, Tuple, Optional

from src.models.data_model import ParserDefinition, Application, NamedFilter
from .block_parser import BlockParser
from .application_parser import ApplicationParser
from .filter_parser import FilterParser

logger = logging.getLogger(__name__)


class SyslogNgParser:
    """
    Main parser for syslog-ng configuration files.
    Orchestrates parsing of block parsers and applications.
    """

    def __init__(self):
        self.block_parser = BlockParser()
        self.application_parser = ApplicationParser()
        self.filter_parser = FilterParser()

    def parse_file(
        self,
        file_path: str,
        content: str,
        extract_raw: bool = False
    ) -> List[ParserDefinition]:
        """
        Parse a complete configuration file.

        Args:
            file_path: Path to the file (for reference)
            content: File content
            extract_raw: Whether to include raw config in output

        Returns:
            List of ParserDefinition objects
        """
        try:
            # Extract block parsers
            block_parsers = self.block_parser.extract_block_parsers(content)

            # Extract applications
            applications = self.application_parser.extract_applications(content)

            # Extract named filters (standalone filter definitions)
            named_filters_raw = self.filter_parser.extract_named_filters(content)

            # Build parser definitions
            parser_defs = self._build_parser_definitions(
                file_path,
                block_parsers,
                applications,
                named_filters_raw,
                content if extract_raw else None
            )

            logger.info(f"Parsed {file_path}: {len(parser_defs)} parsers, {len(applications)} applications, {len(named_filters_raw)} named filters")
            return parser_defs

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            # Return a parser with error info
            return [ParserDefinition(
                name=f"ERROR_{file_path}",
                parser_type="unknown",
                file_path=file_path,
                parse_error=str(e)
            )]

    def _build_parser_definitions(
        self,
        file_path: str,
        block_parsers: List[Tuple[str, str]],
        applications: List[Tuple[str, str, str]],
        named_filters_raw: List[Tuple[str, str]],
        raw_content: Optional[str]
    ) -> List[ParserDefinition]:
        """
        Build ParserDefinition objects from extracted data.

        Args:
            file_path: Path to the configuration file
            block_parsers: List of (parser_name, parser_content) tuples
            applications: List of (app_name, app_type, app_content) tuples
            named_filters_raw: List of (filter_name, filter_content) tuples
            raw_content: Optional raw file content

        Returns:
            List of ParserDefinition objects
        """
        parser_defs = []

        # Parse named filters
        named_filters = []
        for filter_name, filter_content in named_filters_raw:
            filters = self.filter_parser.parse_filter_block(filter_content)
            named_filters.append(NamedFilter(
                name=filter_name,
                filters=filters,
                raw_content=filter_content
            ))

        # Parse each block parser
        for parser_name, parser_content in block_parsers:
            metadata, conditional_rewrites, nested_parsers = \
                self.block_parser.parse_block_parser(parser_name, parser_content)

            # Infer parser type
            parser_type = self.block_parser.infer_parser_type(parser_name, parser_content)

            # Find matching applications
            matching_apps = self._find_matching_applications(
                parser_name,
                applications
            )

            # Create parser definition
            parser_def = ParserDefinition(
                name=parser_name,
                parser_type=parser_type,
                file_path=file_path,
                metadata=metadata,
                applications=matching_apps,
                nested_parsers=nested_parsers,
                conditional_rewrites=conditional_rewrites,
                named_filters=named_filters,
                raw_config=raw_content
            )

            parser_defs.append(parser_def)

        # Handle applications without block parsers
        # (Some files might only have applications that reference parsers from other files)
        orphan_apps = self._find_orphan_applications(block_parsers, applications)

        for app_name, app_type, app_content in orphan_apps:
            app = self.application_parser.parse_application(app_name, app_type, app_content)

            # Create a minimal parser definition for the orphaned application
            parser_def = ParserDefinition(
                name=app_name,
                parser_type="reference",  # Indicates this references a parser from another file
                file_path=file_path,
                applications=[app],
                named_filters=named_filters
            )

            parser_defs.append(parser_def)

        return parser_defs

    def _find_matching_applications(
        self,
        parser_name: str,
        applications: List[Tuple[str, str, str]]
    ) -> List[Application]:
        """
        Find applications that reference a specific parser.

        Args:
            parser_name: Name of the parser
            applications: List of (app_name, app_type, app_content) tuples

        Returns:
            List of Application objects that reference this parser
        """
        matching = []

        for app_name, app_type, app_content in applications:
            app = self.application_parser.parse_application(app_name, app_type, app_content)

            # Check if this application references the parser
            if app.parser_reference == parser_name or app.name == parser_name:
                matching.append(app)

        return matching

    def _find_orphan_applications(
        self,
        block_parsers: List[Tuple[str, str]],
        applications: List[Tuple[str, str, str]]
    ) -> List[Tuple[str, str, str]]:
        """
        Find applications that don't match any block parser in this file.

        Args:
            block_parsers: List of (parser_name, parser_content) tuples
            applications: List of (app_name, app_type, app_content) tuples

        Returns:
            List of orphaned application tuples
        """
        parser_names = {name for name, _ in block_parsers}
        orphans = []

        for app_name, app_type, app_content in applications:
            app = self.application_parser.parse_application(app_name, app_type, app_content)

            # Check if parser reference is in this file
            if app.parser_reference and app.parser_reference not in parser_names:
                # This application references a parser from another file
                orphans.append((app_name, app_type, app_content))

        return orphans

    def parse_multiple_files(
        self,
        files: List[Tuple[str, str]],
        extract_raw: bool = False
    ) -> List[ParserDefinition]:
        """
        Parse multiple configuration files.

        Args:
            files: List of (file_path, content) tuples
            extract_raw: Whether to include raw config in output

        Returns:
            List of all ParserDefinition objects
        """
        all_parsers = []

        for file_path, content in files:
            parsers = self.parse_file(file_path, content, extract_raw)
            all_parsers.extend(parsers)

        logger.info(f"Parsed {len(files)} files, total {len(all_parsers)} parsers")
        return all_parsers
