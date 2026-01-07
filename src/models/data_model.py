"""
Data models for SC4S parser tree representation.
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Metadata:
    """Metadata assigned by a parser."""
    index: Optional[str] = None
    sourcetype: Optional[str] = None
    vendor: Optional[str] = None
    product: Optional[str] = None
    template: Optional[str] = None
    class_: Optional[str] = None  # device_event_class

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class FilterExpression:
    """A filter expression that matches messages."""
    filter_type: str  # 'program', 'message', 'host', 'filter'
    pattern: str  # The pattern to match
    match_type: str = "string"  # 'string', 'regexp', 'glob'
    flags: List[str] = field(default_factory=list)  # 'prefix', 'substring', 'ignore-case'
    raw: Optional[str] = None  # Raw filter expression

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.filter_type,
            "pattern": self.pattern,
            "match_type": self.match_type,
            "flags": self.flags,
            "raw": self.raw
        }


@dataclass
class ConditionalRewrite:
    """A conditional rewrite rule (if/elif/else)."""
    condition: Optional[FilterExpression] = None  # None for 'else'
    metadata: Metadata = field(default_factory=Metadata)
    condition_type: str = "if"  # 'if', 'elif', 'else'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "condition_type": self.condition_type,
            "condition": self.condition.to_dict() if self.condition else None,
            "metadata": self.metadata.to_dict()
        }


@dataclass
class Application:
    """An application block that links filters to parsers."""
    name: str
    app_type: str  # 'sc4s-syslog', 'sc4s-syslog-pgm', 'sc4s-network-source'
    filters: List[FilterExpression] = field(default_factory=list)
    parser_reference: Optional[str] = None  # The parser this application uses

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.app_type,
            "filters": [f.to_dict() for f in self.filters],
            "parser_reference": self.parser_reference
        }


@dataclass
class ParserDefinition:
    """A complete parser definition."""
    name: str  # e.g., 'app-syslog-cisco_asa'
    parser_type: str  # 'syslog', 'json', 'cef', 'leef', 'raw'
    file_path: str
    metadata: Metadata = field(default_factory=Metadata)
    applications: List[Application] = field(default_factory=list)
    nested_parsers: List[str] = field(default_factory=list)  # csv-parser, kv-parser, etc.
    conditional_rewrites: List[ConditionalRewrite] = field(default_factory=list)
    raw_config: Optional[str] = None
    parse_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "name": self.name,
            "type": self.parser_type,
            "file_path": self.file_path,
            "metadata": self.metadata.to_dict(),
            "applications": [app.to_dict() for app in self.applications],
        }

        if self.nested_parsers:
            result["nested_parsers"] = self.nested_parsers

        if self.conditional_rewrites:
            result["conditional_rewrites"] = [cr.to_dict() for cr in self.conditional_rewrites]

        if self.parse_error:
            result["parse_error"] = self.parse_error

        return result


@dataclass
class Product:
    """A vendor product."""
    name: str
    vendor: str
    parsers: List[ParserDefinition] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "vendor": self.vendor,
            "parsers": [p.to_dict() for p in self.parsers]
        }


@dataclass
class Vendor:
    """A vendor (e.g., Cisco, F5, VMware)."""
    name: str
    products: List[Product] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "products": [p.to_dict() for p in self.products]
        }


@dataclass
class SC4STreeData:
    """Complete SC4S parser tree data."""
    vendors: List[Vendor] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize metadata with defaults."""
        if not self.metadata:
            self.metadata = {
                "scraped_at": datetime.utcnow().isoformat() + "Z",
                "repository": "splunk/splunk-connect-for-syslog",
                "branch": "main",
                "total_vendors": 0,
                "total_products": 0,
                "total_parsers": 0
            }

    def update_statistics(self):
        """Update statistics in metadata."""
        total_parsers = sum(
            len(product.parsers)
            for vendor in self.vendors
            for product in vendor.products
        )

        total_products = sum(len(vendor.products) for vendor in self.vendors)

        self.metadata.update({
            "total_vendors": len(self.vendors),
            "total_products": total_products,
            "total_parsers": total_parsers,
            "scraped_at": datetime.utcnow().isoformat() + "Z"
        })

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        self.update_statistics()
        return {
            "metadata": self.metadata,
            "vendors": [v.to_dict() for v in self.vendors]
        }
