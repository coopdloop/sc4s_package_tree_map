"""
Parser for application block definitions.
"""
import re
import logging
from typing import List, Tuple, Optional

from src.models.data_model import Application, FilterExpression
from .filter_parser import FilterParser

logger = logging.getLogger(__name__)


class ApplicationParser:
    """Parse 'application' blocks from syslog-ng configuration."""

    # Pattern to match application definitions
    APPLICATION_PATTERN = re.compile(
        r'application\s+([\w\-]+)\s*\[([\w\-]+)\]\s*\{(.*?)\n\s*\};',
        re.DOTALL | re.IGNORECASE
    )

    # Pattern to extract parser reference
    PARSER_REF_PATTERN = re.compile(
        r'parser\s*\{\s*([\w\-]+)\s*\(\s*\)\s*;?\s*\}',
        re.IGNORECASE
    )

    def __init__(self):
        self.filter_parser = FilterParser()

    def extract_applications(self, content: str) -> List[Tuple[str, str, str]]:
        """
        Extract all application definitions from content.

        Args:
            content: Configuration file content

        Returns:
            List of (app_name, app_type, app_content) tuples
        """
        applications = []

        for match in self.APPLICATION_PATTERN.finditer(content):
            app_name = match.group(1)
            app_type = match.group(2)
            app_content = match.group(3)
            applications.append((app_name, app_type, app_content))

        logger.debug(f"Found {len(applications)} application definitions")
        return applications

    def parse_application(
        self,
        app_name: str,
        app_type: str,
        app_content: str
    ) -> Application:
        """
        Parse a single application block.

        Args:
            app_name: Name of the application
            app_type: Type of application (e.g., 'sc4s-syslog')
            app_content: Content of the application block

        Returns:
            Application object
        """
        # Extract filters
        filters = self._extract_filters(app_content)

        # Extract parser reference
        parser_ref = self._extract_parser_reference(app_content)

        return Application(
            name=app_name,
            app_type=app_type,
            filters=filters,
            parser_reference=parser_ref
        )

    def _extract_filters(self, content: str) -> List[FilterExpression]:
        """
        Extract filter expressions from application content.

        Args:
            content: Application block content

        Returns:
            List of FilterExpression objects
        """
        filters = []

        # Extract filter blocks
        filter_blocks = self.filter_parser.extract_filter_blocks(content)

        for block in filter_blocks:
            block_filters = self.filter_parser.parse_filter_block(block)
            filters.extend(block_filters)

        return filters

    def _extract_parser_reference(self, content: str) -> Optional[str]:
        """
        Extract the parser reference from application content.

        Args:
            content: Application block content

        Returns:
            Parser name or None
        """
        match = self.PARSER_REF_PATTERN.search(content)

        if match:
            return match.group(1)

        return None
