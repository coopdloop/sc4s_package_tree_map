"""
Parser for block parser definitions.
"""
import re
import logging
from typing import Optional, List, Tuple

from src.models.data_model import Metadata, ConditionalRewrite
from .rewrite_parser import RewriteParser

logger = logging.getLogger(__name__)


class BlockParser:
    """Parse 'block parser' definitions from syslog-ng configuration."""

    # Pattern to match block parser definitions
    BLOCK_PARSER_PATTERN = re.compile(
        r'block\s+parser\s+([\w\-]+)\s*\(\s*\)\s*\{(.*?)\n\s*\};',
        re.DOTALL | re.IGNORECASE
    )

    # Pattern to extract nested parser calls
    NESTED_PARSER_PATTERN = re.compile(
        r'(csv-parser|kv-parser|regexp-parser|json-parser|date-parser)\s*\(',
        re.IGNORECASE
    )

    def __init__(self):
        self.rewrite_parser = RewriteParser()

    def extract_block_parsers(self, content: str) -> List[Tuple[str, str]]:
        """
        Extract all block parser definitions from content.

        Args:
            content: Configuration file content

        Returns:
            List of (parser_name, parser_content) tuples
        """
        parsers = []

        for match in self.BLOCK_PARSER_PATTERN.finditer(content):
            parser_name = match.group(1)
            parser_content = match.group(2)
            parsers.append((parser_name, parser_content))

        logger.debug(f"Found {len(parsers)} block parser definitions")
        return parsers

    def parse_block_parser(
        self,
        parser_name: str,
        parser_content: str
    ) -> Tuple[Metadata, List[ConditionalRewrite], List[str]]:
        """
        Parse a single block parser definition.

        Args:
            parser_name: Name of the parser
            parser_content: Content of the parser block

        Returns:
            Tuple of (metadata, conditional_rewrites, nested_parsers)
        """
        # Extract default metadata
        metadata = self.rewrite_parser.parse_r_set_splunk_dest_default(parser_content)

        # Extract conditional rewrites if present
        conditional_rewrites = []
        if self.rewrite_parser.has_conditional_logic(parser_content):
            conditional_rewrites = self.rewrite_parser.parse_conditional_rewrites(parser_content)

        # Extract nested parsers
        nested_parsers = self._extract_nested_parsers(parser_content)

        return metadata, conditional_rewrites, nested_parsers

    def _extract_nested_parsers(self, content: str) -> List[str]:
        """
        Extract nested parser types used within a block parser.

        Args:
            content: Parser block content

        Returns:
            List of nested parser types
        """
        nested = []

        for match in self.NESTED_PARSER_PATTERN.finditer(content):
            parser_type = match.group(1)
            if parser_type not in nested:
                nested.append(parser_type)

        return nested

    def infer_parser_type(self, parser_name: str, parser_content: str) -> str:
        """
        Infer the parser type from name and content.

        Args:
            parser_name: Name of the parser (e.g., 'app-syslog-cisco_asa')
            parser_content: Content of the parser block

        Returns:
            Parser type: 'syslog', 'json', 'cef', 'leef', 'raw', 'unknown'
        """
        name_lower = parser_name.lower()

        # Check name for type indicators
        if 'syslog' in name_lower:
            return 'syslog'
        elif 'json' in name_lower:
            return 'json'
        elif 'cef' in name_lower:
            return 'cef'
        elif 'leef' in name_lower:
            return 'leef'
        elif 'raw' in name_lower:
            return 'raw'

        # Check content for parser type indicators
        content_lower = parser_content.lower()

        if 'json-parser' in content_lower:
            return 'json'
        elif 'cef' in content_lower:
            return 'cef'
        elif 'leef' in content_lower:
            return 'leef'

        # Default to syslog if no other type is clear
        return 'syslog'
