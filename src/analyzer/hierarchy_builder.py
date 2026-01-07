"""
Build vendor/product hierarchy from parser definitions.
"""
import re
import logging
from typing import List, Tuple, Dict
from collections import defaultdict

from src.models.data_model import ParserDefinition, Vendor, Product, SC4STreeData

logger = logging.getLogger(__name__)


class HierarchyBuilder:
    """Build hierarchical structure of vendors and products."""

    # Common vendor name mappings (for edge cases)
    VENDOR_MAPPINGS = {
        'f5': 'F5 Networks',
        'vmware': 'VMware',
        'cisco': 'Cisco',
        'juniper': 'Juniper Networks',
        'paloalto': 'Palo Alto Networks',
        'checkpoint': 'Check Point',
        'microsoft': 'Microsoft',
    }

    def __init__(self):
        self.vendor_product_cache: Dict[str, Tuple[str, str]] = {}

    def build_hierarchy(self, parsers: List[ParserDefinition]) -> SC4STreeData:
        """
        Build complete vendor/product hierarchy from parsers.

        Args:
            parsers: List of ParserDefinition objects

        Returns:
            SC4STreeData with organized hierarchy
        """
        # Group parsers by vendor/product
        vendor_products = defaultdict(lambda: defaultdict(list))

        for parser in parsers:
            vendor, product = self.extract_vendor_product(parser)

            # Skip parsers with errors or that we couldn't categorize
            if vendor and product:
                vendor_products[vendor][product].append(parser)
            else:
                logger.warning(f"Could not categorize parser: {parser.name}")

        # Build vendor objects
        vendors = []

        for vendor_name in sorted(vendor_products.keys()):
            products = []

            for product_name in sorted(vendor_products[vendor_name].keys()):
                product = Product(
                    name=product_name,
                    vendor=vendor_name,
                    parsers=vendor_products[vendor_name][product_name]
                )
                products.append(product)

            vendor = Vendor(
                name=vendor_name,
                products=products
            )
            vendors.append(vendor)

        # Create tree data
        tree_data = SC4STreeData(vendors=vendors)

        logger.info(
            f"Built hierarchy: {len(vendors)} vendors, "
            f"{sum(len(v.products) for v in vendors)} products, "
            f"{len(parsers)} parsers"
        )

        return tree_data

    def extract_vendor_product(self, parser: ParserDefinition) -> Tuple[str, str]:
        """
        Extract vendor and product names from a parser.

        Args:
            parser: ParserDefinition object

        Returns:
            Tuple of (vendor_name, product_name)
        """
        # Check cache first
        if parser.name in self.vendor_product_cache:
            return self.vendor_product_cache[parser.name]

        vendor = None
        product = None

        # Strategy 1: Use metadata if available
        if parser.metadata.vendor and parser.metadata.product:
            vendor = parser.metadata.vendor
            product = parser.metadata.product

        # Strategy 2: Extract from parser name
        else:
            vendor, product = self._extract_from_name(parser.name)

            # Validate against metadata if available
            if parser.metadata.vendor and vendor:
                # Use metadata vendor if different (metadata is more reliable)
                if parser.metadata.vendor.lower() != vendor.lower():
                    logger.debug(
                        f"Using metadata vendor '{parser.metadata.vendor}' "
                        f"instead of parsed '{vendor}' for {parser.name}"
                    )
                    vendor = parser.metadata.vendor

            if parser.metadata.product and product:
                if parser.metadata.product.lower() != product.lower():
                    logger.debug(
                        f"Using metadata product '{parser.metadata.product}' "
                        f"instead of parsed '{product}' for {parser.name}"
                    )
                    product = parser.metadata.product

        # Apply vendor name mapping
        if vendor:
            vendor = self._normalize_vendor_name(vendor)

        # Normalize product name
        if product:
            product = self._normalize_product_name(product)

        # Cache the result
        self.vendor_product_cache[parser.name] = (vendor, product)

        return vendor, product

    def _extract_from_name(self, parser_name: str) -> Tuple[str, str]:
        """
        Extract vendor and product from parser name.

        Parser naming pattern: app-[type]-[vendor]_[product]
        Examples:
            app-syslog-cisco_asa         -> cisco, asa
            app-syslog-f5_bigip          -> f5, bigip
            app-json-zscaler_lss         -> zscaler, lss
            app-syslog-vmware_cb-protect -> vmware, cb-protect

        Args:
            parser_name: Parser name

        Returns:
            Tuple of (vendor, product)
        """
        # Remove common prefixes
        name = parser_name
        for prefix in ['app-syslog-', 'app-json-', 'app-cef-', 'app-leef-', 'app-raw-', 'app-netsource-']:
            if name.startswith(prefix):
                name = name[len(prefix):]
                break

        # Split on first underscore
        if '_' in name:
            parts = name.split('_', 1)
            vendor = parts[0]
            product = parts[1] if len(parts) > 1 else 'unknown'
        else:
            # No underscore - use entire name as vendor
            vendor = name
            product = 'default'

        return vendor, product

    def _normalize_vendor_name(self, vendor: str) -> str:
        """
        Normalize vendor name to a standard format.

        Args:
            vendor: Raw vendor name

        Returns:
            Normalized vendor name
        """
        vendor_lower = vendor.lower()

        # Check mappings
        if vendor_lower in self.VENDOR_MAPPINGS:
            return self.VENDOR_MAPPINGS[vendor_lower]

        # Capitalize each word
        return vendor.replace('_', ' ').replace('-', ' ').title()

    def _normalize_product_name(self, product: str) -> str:
        """
        Normalize product name to a standard format.

        Args:
            product: Raw product name

        Returns:
            Normalized product name
        """
        # Keep hyphens and underscores, but capitalize properly
        # Examples: cb-protect -> CB-Protect, bigip -> BIG-IP

        # Special cases
        special_cases = {
            'bigip': 'BIG-IP',
            'asa': 'ASA',
            'ios': 'IOS',
            'nxos': 'NX-OS',
            'iosxe': 'IOS-XE',
        }

        product_lower = product.lower()
        if product_lower in special_cases:
            return special_cases[product_lower]

        # Default: capitalize with proper handling of hyphens
        return product.replace('_', '-').upper() if len(product) <= 4 else product.replace('_', '-').title()
