"""
Parser for rewrite rules and metadata extraction.
"""
import re
import logging
from typing import Optional, Dict, List

from src.models.data_model import Metadata, ConditionalRewrite, FilterExpression

logger = logging.getLogger(__name__)


class RewriteParser:
    """Parse rewrite blocks and extract metadata."""

    # Pattern to match r_set_splunk_dest_default() calls - updated to handle nested parens
    # This pattern finds the function name, then uses a helper method to extract the full call
    SPLUNK_DEST_START_PATTERN = re.compile(
        r'r_set_splunk_dest_default\s*\(',
        re.DOTALL
    )

    # Pattern to match individual field assignments
    FIELD_PATTERN = re.compile(
        r"(\w+)\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
    )

    # Pattern to match conditional blocks
    IF_PATTERN = re.compile(
        r'\bif\s*\(',
        re.IGNORECASE
    )

    ELIF_PATTERN = re.compile(
        r'\belif\s*\(',
        re.IGNORECASE
    )

    ELSE_PATTERN = re.compile(
        r'\belse\s*\{',
        re.IGNORECASE
    )

    def parse_r_set_splunk_dest_default(self, content: str) -> Metadata:
        """
        Extract metadata from r_set_splunk_dest_default() call.

        Args:
            content: Content containing the function call

        Returns:
            Metadata object with extracted fields
        """
        match = self.SPLUNK_DEST_START_PATTERN.search(content)

        if not match:
            logger.debug("No r_set_splunk_dest_default found")
            return Metadata()

        # Find matching closing parenthesis
        start_pos = match.end()
        body = self._extract_balanced_parens(content, start_pos - 1)

        if not body:
            logger.debug("Could not extract balanced parentheses")
            return Metadata()

        # Extract all field(value) pairs
        fields = {}
        for field_match in self.FIELD_PATTERN.finditer(body):
            field_name = field_match.group(1)
            field_value = field_match.group(2)
            fields[field_name] = field_value

        return Metadata(
            index=fields.get('index'),
            sourcetype=fields.get('sourcetype'),
            vendor=fields.get('vendor'),
            product=fields.get('product'),
            template=fields.get('template'),
            class_=fields.get('class')
        )

    def _extract_balanced_parens(self, content: str, start_pos: int) -> str:
        """
        Extract content within balanced parentheses starting at start_pos.

        Args:
            content: Full content string
            start_pos: Position of opening parenthesis

        Returns:
            Content within the balanced parentheses (excluding the parens themselves)
        """
        if start_pos >= len(content) or content[start_pos] != '(':
            return ""

        paren_count = 1
        pos = start_pos + 1
        start_content = pos

        while pos < len(content) and paren_count > 0:
            if content[pos] == '(':
                paren_count += 1
            elif content[pos] == ')':
                paren_count -= 1
            pos += 1

        if paren_count == 0:
            # Found matching closing paren
            return content[start_content:pos-1]
        else:
            # Unbalanced parentheses
            return ""

    def extract_rewrite_blocks(self, content: str) -> List[str]:
        """
        Extract all rewrite blocks from content.

        Args:
            content: Configuration file content

        Returns:
            List of rewrite block contents
        """
        rewrite_blocks = []

        # Find all rewrite { ... } blocks
        pattern = re.compile(r'rewrite\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}', re.DOTALL)

        for match in pattern.finditer(content):
            rewrite_blocks.append(match.group(1))

        return rewrite_blocks

    def parse_conditional_rewrites(self, content: str) -> List[ConditionalRewrite]:
        """
        Parse conditional rewrite rules (if/elif/else).

        Args:
            content: Content containing conditional blocks

        Returns:
            List of ConditionalRewrite objects
        """
        conditional_rewrites = []

        # This is a simplified parser - handles basic if/elif/else
        # More complex nested conditions would need a proper AST parser

        # Find if blocks
        if_matches = list(re.finditer(
            r'if\s*\((.*?)\)\s*\{(.*?)\}',
            content,
            re.DOTALL | re.IGNORECASE
        ))

        for match in if_matches:
            condition_expr = match.group(1).strip()
            block_content = match.group(2)

            # Extract filter from condition
            filter_expr = self._parse_condition_filter(condition_expr)

            # Extract metadata from rewrite block
            metadata = self.parse_r_set_splunk_dest_default(block_content)

            conditional_rewrites.append(ConditionalRewrite(
                condition=filter_expr,
                metadata=metadata,
                condition_type='if'
            ))

        # Find elif blocks
        elif_matches = list(re.finditer(
            r'elif\s*\((.*?)\)\s*\{(.*?)\}',
            content,
            re.DOTALL | re.IGNORECASE
        ))

        for match in elif_matches:
            condition_expr = match.group(1).strip()
            block_content = match.group(2)

            filter_expr = self._parse_condition_filter(condition_expr)
            metadata = self.parse_r_set_splunk_dest_default(block_content)

            conditional_rewrites.append(ConditionalRewrite(
                condition=filter_expr,
                metadata=metadata,
                condition_type='elif'
            ))

        # Find else blocks
        else_matches = list(re.finditer(
            r'else\s*\{(.*?)\}',
            content,
            re.DOTALL | re.IGNORECASE
        ))

        for match in else_matches:
            block_content = match.group(1)
            metadata = self.parse_r_set_splunk_dest_default(block_content)

            conditional_rewrites.append(ConditionalRewrite(
                condition=None,
                metadata=metadata,
                condition_type='else'
            ))

        return conditional_rewrites

    def _parse_condition_filter(self, condition: str) -> Optional[FilterExpression]:
        """
        Parse a condition expression into a FilterExpression.

        Args:
            condition: Condition string (e.g., "message('SSL_ERROR')")

        Returns:
            FilterExpression or None
        """
        # Simple parsing - look for common filter patterns
        # program(), message(), host()

        filter_match = re.search(
            r'(program|message|host)\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
            condition,
            re.IGNORECASE
        )

        if filter_match:
            filter_type = filter_match.group(1).lower()
            pattern = filter_match.group(2)

            # Check for type and flags
            match_type = 'string'
            flags = []

            type_match = re.search(r'type\s*\(\s*(\w+)\s*\)', condition)
            if type_match:
                match_type = type_match.group(1)

            flags_match = re.search(r'flags\s*\(\s*([^)]+)\s*\)', condition)
            if flags_match:
                flags_str = flags_match.group(1)
                flags = [f.strip() for f in flags_str.split(',')]

            return FilterExpression(
                filter_type=filter_type,
                pattern=pattern,
                match_type=match_type,
                flags=flags,
                raw=condition
            )

        # If we can't parse it, just store the raw condition
        return FilterExpression(
            filter_type='filter',
            pattern=condition,
            raw=condition
        )

    def has_conditional_logic(self, content: str) -> bool:
        """
        Check if content has conditional rewrite logic.

        Args:
            content: Configuration content

        Returns:
            True if conditional logic is present
        """
        return bool(
            self.IF_PATTERN.search(content) or
            self.ELIF_PATTERN.search(content) or
            self.ELSE_PATTERN.search(content)
        )
