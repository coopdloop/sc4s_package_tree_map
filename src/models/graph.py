"""
Build D3.js-compatible hierarchical graph structure.
"""
import logging
from typing import Dict, Any, List
from collections import defaultdict

from .data_model import SC4STreeData, Vendor, Product, ParserDefinition

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Build hierarchical graph structures for visualization."""

    def build_vendor_hierarchy(self, tree_data: SC4STreeData) -> Dict[str, Any]:
        """
        Build vendor-based hierarchy for D3.js tree.

        Structure: Root → Vendor → Product → Parser

        Args:
            tree_data: SC4STreeData object

        Returns:
            D3.js-compatible hierarchical data
        """
        root = {
            "name": "SC4S Parsers",
            "type": "root",
            "children": []
        }

        for vendor in tree_data.vendors:
            vendor_node = {
                "name": vendor.name,
                "type": "vendor",
                "children": [],
                "metadata": {
                    "product_count": len(vendor.products),
                    "parser_count": sum(len(p.parsers) for p in vendor.products)
                }
            }

            for product in vendor.products:
                product_node = {
                    "name": product.name,
                    "type": "product",
                    "vendor": vendor.name,
                    "children": [],
                    "metadata": {
                        "parser_count": len(product.parsers)
                    }
                }

                for parser in product.parsers:
                    parser_node = self._build_parser_node(parser, vendor.name, product.name)
                    product_node["children"].append(parser_node)

                vendor_node["children"].append(product_node)

            root["children"].append(vendor_node)

        return root

    def build_type_hierarchy(self, tree_data: SC4STreeData) -> Dict[str, Any]:
        """
        Build parser-type-based hierarchy.

        Structure: Root → Parser Type → Vendor → Parser

        Args:
            tree_data: SC4STreeData object

        Returns:
            D3.js-compatible hierarchical data
        """
        root = {
            "name": "SC4S Parsers by Type",
            "type": "root",
            "children": []
        }

        # Group parsers by type
        type_groups = defaultdict(lambda: defaultdict(list))

        for vendor in tree_data.vendors:
            for product in vendor.products:
                for parser in product.parsers:
                    type_groups[parser.parser_type][vendor.name].append(
                        (parser, product.name)
                    )

        # Build hierarchy
        for parser_type in sorted(type_groups.keys()):
            type_node = {
                "name": parser_type.upper(),
                "type": "parser_type",
                "children": []
            }

            for vendor_name in sorted(type_groups[parser_type].keys()):
                vendor_node = {
                    "name": vendor_name,
                    "type": "vendor",
                    "children": []
                }

                for parser, product_name in type_groups[parser_type][vendor_name]:
                    parser_node = self._build_parser_node(parser, vendor_name, product_name)
                    vendor_node["children"].append(parser_node)

                type_node["children"].append(vendor_node)

            root["children"].append(type_node)

        return root

    def build_index_hierarchy(self, tree_data: SC4STreeData) -> Dict[str, Any]:
        """
        Build index-based hierarchy.

        Structure: Root → Index → Vendor → Parser

        Args:
            tree_data: SC4STreeData object

        Returns:
            D3.js-compatible hierarchical data
        """
        root = {
            "name": "SC4S Parsers by Index",
            "type": "root",
            "children": []
        }

        # Group parsers by index
        index_groups = defaultdict(lambda: defaultdict(list))

        for vendor in tree_data.vendors:
            for product in vendor.products:
                for parser in product.parsers:
                    index = parser.metadata.index or "unknown"
                    index_groups[index][vendor.name].append((parser, product.name))

        # Build hierarchy
        for index_name in sorted(index_groups.keys()):
            index_node = {
                "name": index_name,
                "type": "index",
                "children": []
            }

            for vendor_name in sorted(index_groups[index_name].keys()):
                vendor_node = {
                    "name": vendor_name,
                    "type": "vendor",
                    "children": []
                }

                for parser, product_name in index_groups[index_name][vendor_name]:
                    parser_node = self._build_parser_node(parser, vendor_name, product_name)
                    vendor_node["children"].append(parser_node)

                index_node["children"].append(vendor_node)

            root["children"].append(index_node)

        return root

    def _build_parser_node(
        self,
        parser: ParserDefinition,
        vendor: str,
        product: str
    ) -> Dict[str, Any]:
        """
        Build a parser node with all details.

        Args:
            parser: ParserDefinition object
            vendor: Vendor name
            product: Product name

        Returns:
            Parser node dictionary
        """
        node = {
            "name": parser.name,
            "type": "parser",
            "parser_type": parser.parser_type,
            "vendor": vendor,
            "product": product,
            "file_path": parser.file_path,
            "metadata": parser.metadata.to_dict(),
            "applications": [app.to_dict() for app in parser.applications],
        }

        if parser.nested_parsers:
            node["nested_parsers"] = parser.nested_parsers

        if parser.conditional_rewrites:
            node["conditional_rewrites"] = [cr.to_dict() for cr in parser.conditional_rewrites]

        if parser.parse_error:
            node["parse_error"] = parser.parse_error

        return node

    def build_all_views(self, tree_data: SC4STreeData) -> Dict[str, Dict[str, Any]]:
        """
        Build all view hierarchies.

        Args:
            tree_data: SC4STreeData object

        Returns:
            Dictionary with all views
        """
        return {
            "vendor": self.build_vendor_hierarchy(tree_data),
            "type": self.build_type_hierarchy(tree_data),
            "index": self.build_index_hierarchy(tree_data)
        }

    def build_flat_list(self, tree_data: SC4STreeData) -> List[Dict[str, Any]]:
        """
        Build a flat list of all parsers for search.

        Args:
            tree_data: SC4STreeData object

        Returns:
            List of parser dictionaries
        """
        parsers = []

        for vendor in tree_data.vendors:
            for product in vendor.products:
                for parser in product.parsers:
                    parser_dict = self._build_parser_node(parser, vendor.name, product.name)
                    parsers.append(parser_dict)

        return parsers
