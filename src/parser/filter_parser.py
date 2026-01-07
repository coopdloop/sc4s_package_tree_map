"""
Parser for filter expressions.
"""
import re
import logging
from typing import List, Optional

from src.models.data_model import FilterExpression

logger = logging.getLogger(__name__)


class FilterParser:
    """Parse filter expressions from syslog-ng configuration."""

    # Common filter patterns
    PROGRAM_PATTERN = re.compile(
        r"program\s*\(\s*['\"]([^'\"]+)['\"]\s*(?:type\s*\(\s*(\w+)\s*\))?\s*(?:flags\s*\(\s*([^)]+)\s*\))?\s*\)",
        re.IGNORECASE
    )

    MESSAGE_PATTERN = re.compile(
        r"message\s*\(\s*['\"]([^'\"]+)['\"]\s*(?:type\s*\(\s*(\w+)\s*\))?\s*(?:flags\s*\(\s*([^)]+)\s*\))?\s*\)",
        re.IGNORECASE
    )

    HOST_PATTERN = re.compile(
        r"host\s*\(\s*['\"]([^'\"]+)['\"]\s*(?:type\s*\(\s*(\w+)\s*\))?\s*(?:flags\s*\(\s*([^)]+)\s*\))?\s*\)",
        re.IGNORECASE
    )

    # Generic filter pattern
    FILTER_FUNC_PATTERN = re.compile(
        r"(\w+)\s*\(\s*['\"]([^'\"]+)['\"]\s*([^)]*)\)",
        re.IGNORECASE
    )

    def parse_filter_block(self, content: str) -> List[FilterExpression]:
        """
        Parse a filter block and extract all filter expressions.

        Args:
            content: Content of a filter block

        Returns:
            List of FilterExpression objects
        """
        filters = []

        # Try to match specific filter types first
        filters.extend(self._parse_program_filters(content))
        filters.extend(self._parse_message_filters(content))
        filters.extend(self._parse_host_filters(content))

        # If no specific filters found, try generic parsing
        if not filters:
            filters.extend(self._parse_generic_filters(content))

        return filters

    def _parse_program_filters(self, content: str) -> List[FilterExpression]:
        """Parse program() filters."""
        filters = []

        for match in self.PROGRAM_PATTERN.finditer(content):
            pattern = match.group(1)
            match_type = match.group(2) or 'string'
            flags_str = match.group(3) or ''

            flags = self._parse_flags(flags_str)

            filters.append(FilterExpression(
                filter_type='program',
                pattern=pattern,
                match_type=match_type,
                flags=flags,
                raw=match.group(0)
            ))

        return filters

    def _parse_message_filters(self, content: str) -> List[FilterExpression]:
        """Parse message() filters."""
        filters = []

        for match in self.MESSAGE_PATTERN.finditer(content):
            pattern = match.group(1)
            match_type = match.group(2) or 'string'
            flags_str = match.group(3) or ''

            flags = self._parse_flags(flags_str)

            filters.append(FilterExpression(
                filter_type='message',
                pattern=pattern,
                match_type=match_type,
                flags=flags,
                raw=match.group(0)
            ))

        return filters

    def _parse_host_filters(self, content: str) -> List[FilterExpression]:
        """Parse host() filters."""
        filters = []

        for match in self.HOST_PATTERN.finditer(content):
            pattern = match.group(1)
            match_type = match.group(2) or 'string'
            flags_str = match.group(3) or ''

            flags = self._parse_flags(flags_str)

            filters.append(FilterExpression(
                filter_type='host',
                pattern=pattern,
                match_type=match_type,
                flags=flags,
                raw=match.group(0)
            ))

        return filters

    def _parse_generic_filters(self, content: str) -> List[FilterExpression]:
        """Parse generic filter functions."""
        filters = []

        for match in self.FILTER_FUNC_PATTERN.finditer(content):
            func_name = match.group(1)
            pattern = match.group(2)
            options = match.group(3)

            # Skip if it's a function we already handled
            if func_name.lower() in ['program', 'message', 'host']:
                continue

            # Parse type and flags from options
            match_type = 'string'
            flags = []

            if options:
                type_match = re.search(r'type\s*\(\s*(\w+)\s*\)', options)
                if type_match:
                    match_type = type_match.group(1)

                flags_match = re.search(r'flags\s*\(\s*([^)]+)\s*\)', options)
                if flags_match:
                    flags = self._parse_flags(flags_match.group(1))

            filters.append(FilterExpression(
                filter_type=func_name.lower(),
                pattern=pattern,
                match_type=match_type,
                flags=flags,
                raw=match.group(0)
            ))

        return filters

    def _parse_flags(self, flags_str: str) -> List[str]:
        """
        Parse flags string into list.

        Args:
            flags_str: Flags string (e.g., "prefix, ignore-case")

        Returns:
            List of flag names
        """
        if not flags_str:
            return []

        # Split by comma and clean up
        flags = [f.strip().strip('"\'') for f in flags_str.split(',')]
        return [f for f in flags if f]

    def extract_filter_blocks(self, content: str) -> List[str]:
        """
        Extract filter block contents from configuration.

        Args:
            content: Configuration file content

        Returns:
            List of filter block contents
        """
        filter_blocks = []

        # Find all filter { ... } blocks
        # Handle nested braces
        pattern = re.compile(
            r'filter\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}',
            re.DOTALL
        )

        for match in pattern.finditer(content):
            filter_blocks.append(match.group(1))

        return filter_blocks

    def parse_inline_filter(self, filter_str: str) -> Optional[FilterExpression]:
        """
        Parse a single inline filter expression.

        Args:
            filter_str: Single filter expression

        Returns:
            FilterExpression or None
        """
        filters = self.parse_filter_block(filter_str)
        return filters[0] if filters else None
