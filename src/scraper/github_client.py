"""
GitHub API client for fetching SC4S configuration files.
"""
import time
import logging
from typing import List, Dict, Optional, Tuple
from github import Github, GithubException, RateLimitExceededException
from github.Repository import Repository
from github.ContentFile import ContentFile

logger = logging.getLogger(__name__)


class RateLimiter:
    """Manage GitHub API rate limits."""

    def __init__(self, buffer: int = 10):
        """
        Initialize rate limiter.

        Args:
            buffer: Number of requests to keep as buffer before waiting
        """
        self.buffer = buffer
        self.remaining = None
        self.reset_time = None

    def check_and_wait(self, github_client: Github):
        """
        Check rate limit and wait if necessary.

        Args:
            github_client: PyGithub client instance
        """
        rate_limit = github_client.get_rate_limit()

        # Access core rate limit from resources
        core_rate = rate_limit.resources.core

        self.remaining = core_rate.remaining
        self.reset_time = core_rate.reset.timestamp()

        if self.remaining < self.buffer:
            wait_time = (self.reset_time - time.time()) + 5  # Add 5 sec buffer
            if wait_time > 0:
                logger.warning(
                    f"Rate limit nearly exceeded ({self.remaining} remaining). "
                    f"Waiting {wait_time:.0f} seconds until reset..."
                )
                time.sleep(wait_time)
                # Refresh rate limit info
                rate_limit = github_client.get_rate_limit()
                core_rate = rate_limit.resources.core
                self.remaining = core_rate.remaining

    def get_status(self, github_client: Github) -> Dict[str, int]:
        """Get current rate limit status."""
        rate_limit = github_client.get_rate_limit()

        # Access core rate limit from resources
        core_rate = rate_limit.resources.core

        return {
            "limit": core_rate.limit,
            "remaining": core_rate.remaining,
            "reset": int(core_rate.reset.timestamp())
        }


class GitHubClient:
    """Client for GitHub API interactions."""

    def __init__(self, token: Optional[str] = None, rate_limit_buffer: int = 10):
        """
        Initialize GitHub client.

        Args:
            token: GitHub personal access token (optional but recommended)
            rate_limit_buffer: Number of API calls to keep as buffer
        """
        self.github = Github(token) if token else Github()
        self.rate_limiter = RateLimiter(buffer=rate_limit_buffer)
        self._repo_cache: Optional[Repository] = None

        # Log authentication status
        try:
            user = self.github.get_user()
            logger.info(f"Authenticated as: {user.login}")
        except GithubException:
            logger.warning("Running unauthenticated (60 req/hour limit)")

    def get_repository(self, repo_name: str) -> Repository:
        """
        Get a GitHub repository.

        Args:
            repo_name: Repository name (e.g., 'splunk/splunk-connect-for-syslog')

        Returns:
            Repository object
        """
        if self._repo_cache is None:
            self.rate_limiter.check_and_wait(self.github)
            self._repo_cache = self.github.get_repo(repo_name)
            logger.info(f"Loaded repository: {repo_name}")

        return self._repo_cache

    def get_directory_contents(
        self,
        repo: Repository,
        path: str,
        ref: str = "main"
    ) -> List[ContentFile]:
        """
        Get contents of a directory in the repository.

        Args:
            repo: Repository object
            path: Path to directory
            ref: Branch/commit reference

        Returns:
            List of ContentFile objects
        """
        self.rate_limiter.check_and_wait(self.github)

        try:
            contents = repo.get_contents(path, ref=ref)
            if isinstance(contents, list):
                return contents
            return [contents]
        except GithubException as e:
            if e.status == 404:
                logger.warning(f"Path not found: {path}")
                return []
            raise

    def get_file_content(
        self,
        repo: Repository,
        path: str,
        ref: str = "main"
    ) -> Optional[str]:
        """
        Get content of a file.

        Args:
            repo: Repository object
            path: Path to file
            ref: Branch/commit reference

        Returns:
            File content as string, or None if not found
        """
        self.rate_limiter.check_and_wait(self.github)

        try:
            content_file = repo.get_contents(path, ref=ref)
            if isinstance(content_file, list):
                logger.warning(f"Path is a directory, not a file: {path}")
                return None

            return content_file.decoded_content.decode('utf-8')
        except GithubException as e:
            if e.status == 404:
                logger.warning(f"File not found: {path}")
                return None
            raise

    def get_tree_recursive(
        self,
        repo: Repository,
        path: str,
        ref: str = "main",
        file_extension: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """
        Recursively get all files in a directory tree.

        Args:
            repo: Repository object
            path: Path to directory
            ref: Branch/commit reference
            file_extension: Filter by file extension (e.g., '.conf')

        Returns:
            List of (file_path, file_type) tuples
        """
        results = []

        def _traverse(current_path: str):
            contents = self.get_directory_contents(repo, current_path, ref)

            for content in contents:
                if content.type == "dir":
                    # Recursively traverse directories
                    _traverse(content.path)
                elif content.type == "file":
                    # Check file extension filter
                    if file_extension is None or content.path.endswith(file_extension):
                        results.append((content.path, content.type))

        _traverse(path)
        return results

    def fetch_multiple_files(
        self,
        repo: Repository,
        file_paths: List[str],
        ref: str = "main"
    ) -> List[Tuple[str, Optional[str]]]:
        """
        Fetch multiple files in batch.

        Args:
            repo: Repository object
            file_paths: List of file paths
            ref: Branch/commit reference

        Returns:
            List of (file_path, content) tuples
        """
        results = []

        for file_path in file_paths:
            content = self.get_file_content(repo, file_path, ref)
            results.append((file_path, content))

            # Log progress
            if len(results) % 10 == 0:
                logger.info(f"Fetched {len(results)}/{len(file_paths)} files...")

        return results

    def get_rate_limit_status(self) -> Dict[str, int]:
        """Get current rate limit status."""
        return self.rate_limiter.get_status(self.github)
