"""
File fetcher with caching for SC4S configuration files.
"""
import os
import json
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta

from github.Repository import Repository

from .github_client import GitHubClient

logger = logging.getLogger(__name__)


class FileFetcher:
    """Fetch and cache configuration files from GitHub."""

    def __init__(
        self,
        client: GitHubClient,
        cache_dir: str,
        cache_ttl_hours: int = 24
    ):
        """
        Initialize file fetcher.

        Args:
            client: GitHubClient instance
            cache_dir: Directory for cached files
            cache_ttl_hours: Cache time-to-live in hours
        """
        self.client = client
        self.cache_dir = Path(cache_dir)
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.cache_index_file = self.cache_dir / "cache_index.json"

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load cache index
        self.cache_index = self._load_cache_index()

    def _load_cache_index(self) -> Dict:
        """Load cache index from disk."""
        if self.cache_index_file.exists():
            try:
                with open(self.cache_index_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Corrupted cache index, starting fresh")
                return {}
        return {}

    def _save_cache_index(self):
        """Save cache index to disk."""
        with open(self.cache_index_file, 'w') as f:
            json.dump(self.cache_index, f, indent=2)

    def _get_cache_path(self, file_path: str) -> Path:
        """
        Get cache file path for a given file.

        Args:
            file_path: Original file path from GitHub

        Returns:
            Path to cached file
        """
        # Create a hash of the file path to avoid filesystem issues
        path_hash = hashlib.md5(file_path.encode()).hexdigest()
        # Also keep the filename for readability
        filename = Path(file_path).name
        return self.cache_dir / f"{path_hash}_{filename}"

    def _is_cache_valid(self, file_path: str) -> bool:
        """
        Check if cached file is still valid.

        Args:
            file_path: Original file path from GitHub

        Returns:
            True if cache is valid and not expired
        """
        if file_path not in self.cache_index:
            return False

        cache_info = self.cache_index[file_path]
        cache_time = datetime.fromisoformat(cache_info['cached_at'])
        cache_file = Path(cache_info['cache_path'])

        # Check if cache file exists and is not expired
        if not cache_file.exists():
            return False

        age = datetime.now() - cache_time
        return age < self.cache_ttl

    def get_cached_file(self, file_path: str) -> Optional[str]:
        """
        Get file content from cache if available.

        Args:
            file_path: Original file path from GitHub

        Returns:
            File content or None if not cached
        """
        if not self._is_cache_valid(file_path):
            return None

        cache_path = Path(self.cache_index[file_path]['cache_path'])
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                logger.debug(f"Cache hit: {file_path}")
                return f.read()
        except Exception as e:
            logger.warning(f"Failed to read cache for {file_path}: {e}")
            return None

    def save_to_cache(self, file_path: str, content: str):
        """
        Save file content to cache.

        Args:
            file_path: Original file path from GitHub
            content: File content
        """
        cache_path = self._get_cache_path(file_path)

        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Update cache index
            self.cache_index[file_path] = {
                'cache_path': str(cache_path),
                'cached_at': datetime.now().isoformat(),
                'size': len(content)
            }
            self._save_cache_index()
            logger.debug(f"Cached: {file_path}")

        except Exception as e:
            logger.error(f"Failed to cache {file_path}: {e}")

    def fetch_file(
        self,
        repo: Repository,
        file_path: str,
        ref: str = "main",
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> Optional[str]:
        """
        Fetch a file, using cache if available.

        Args:
            repo: Repository object
            file_path: Path to file in repository
            ref: Branch/commit reference
            use_cache: Whether to use cache
            force_refresh: Force refresh from GitHub even if cached

        Returns:
            File content or None if not found
        """
        # Check cache first
        if use_cache and not force_refresh:
            cached_content = self.get_cached_file(file_path)
            if cached_content is not None:
                return cached_content

        # Fetch from GitHub
        logger.debug(f"Fetching from GitHub: {file_path}")
        content = self.client.get_file_content(repo, file_path, ref)

        if content is not None and use_cache:
            self.save_to_cache(file_path, content)

        return content

    def fetch_directory(
        self,
        repo: Repository,
        directory_path: str,
        ref: str = "main",
        file_extension: str = ".conf",
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> List[Tuple[str, str]]:
        """
        Fetch all files from a directory.

        Args:
            repo: Repository object
            directory_path: Path to directory
            ref: Branch/commit reference
            file_extension: Filter by file extension
            use_cache: Whether to use cache
            force_refresh: Force refresh all files

        Returns:
            List of (file_path, content) tuples
        """
        logger.info(f"Fetching directory: {directory_path}")

        # Get all files in directory tree
        file_paths = self.client.get_tree_recursive(
            repo,
            directory_path,
            ref,
            file_extension
        )

        logger.info(f"Found {len(file_paths)} files in {directory_path}")

        results = []
        for file_path, _ in file_paths:
            content = self.fetch_file(repo, file_path, ref, use_cache, force_refresh)
            if content is not None:
                results.append((file_path, content))

        logger.info(f"Successfully fetched {len(results)}/{len(file_paths)} files")
        return results

    def fetch_all_parsers(
        self,
        repo: Repository,
        base_path: str = "package/etc/conf.d",
        ref: str = "main",
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> List[Tuple[str, str]]:
        """
        Fetch all parser configuration files from SC4S repository.

        Args:
            repo: Repository object
            base_path: Base path to conf.d directory
            ref: Branch/commit reference
            use_cache: Whether to use cache
            force_refresh: Force refresh all files

        Returns:
            List of (file_path, content) tuples
        """
        all_files = []

        # Directories to fetch
        parser_dirs = [
            f"{base_path}/conflib/syslog",
            f"{base_path}/conflib/json",
            f"{base_path}/conflib/cef",
            f"{base_path}/conflib/leef",
            f"{base_path}/conflib/raw",
            f"{base_path}/sources",
        ]

        for parser_dir in parser_dirs:
            logger.info(f"Fetching parsers from: {parser_dir}")
            files = self.fetch_directory(
                repo,
                parser_dir,
                ref,
                file_extension=".conf",
                use_cache=use_cache,
                force_refresh=force_refresh
            )
            all_files.extend(files)

        logger.info(f"Total parser files fetched: {len(all_files)}")
        return all_files

    def clear_cache(self):
        """Clear all cached files."""
        for file_path in list(self.cache_index.keys()):
            cache_path = Path(self.cache_index[file_path]['cache_path'])
            if cache_path.exists():
                cache_path.unlink()

        self.cache_index = {}
        self._save_cache_index()
        logger.info("Cache cleared")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        total_files = len(self.cache_index)
        total_size = sum(info['size'] for info in self.cache_index.values())
        valid_files = sum(1 for fp in self.cache_index if self._is_cache_valid(fp))

        return {
            "total_files": total_files,
            "valid_files": valid_files,
            "expired_files": total_files - valid_files,
            "total_size_bytes": total_size,
            "cache_dir": str(self.cache_dir)
        }
