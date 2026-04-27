"""Filesystem security guard."""

from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


class FileGuard:
    """Prevents access outside the working directory."""
    
    BLOCKED_PATHS = [
        ".env",
        ".env.local",
        ".env.production",
        "id_rsa",
        "id_ed25519",
        ".ssh",
        ".aws",
        ".docker",
        ".kube",
        "secrets.yaml",
        "secrets.json",
    ]
    
    def __init__(self, working_dir: Path) -> None:
        self.working_dir = working_dir.resolve()
        self.blocked_patterns = [p.lower() for p in self.BLOCKED_PATHS]
    
    def check_path(self, path: str | Path) -> Path:
        """Validate a path is within working directory and not blocked."""
        target = Path(path).expanduser().resolve()
        
        try:
            target.relative_to(self.working_dir)
        except ValueError:
            raise PermissionError(
                f"Access denied: {target} is outside working directory {self.working_dir}"
            )
        
        path_str = str(target).lower()
        for blocked in self.blocked_patterns:
            if blocked in path_str:
                raise PermissionError(f"Access denied: {target} matches blocked pattern '{blocked}'")
        
        return target
    
    def is_text_file(self, path: Path, max_size_mb: float = 1.0) -> bool:
        """Check if file is a readable text file."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        if not path.is_file():
            raise ValueError(f"Not a file: {path}")
        
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            raise ValueError(f"File too large: {size_mb:.1f}MB > {max_size_mb}MB limit")
        
        with open(path, "rb") as f:
            chunk = f.read(8192)
            if b"\x00" in chunk:
                raise ValueError(f"Binary file detected: {path}")
        
        return True
    
    def get_relative_path(self, path: Path) -> str:
        """Get path relative to working directory."""
        try:
            return str(path.relative_to(self.working_dir))
        except ValueError:
            return str(path)


class GitAwareness:
    """Detects git repository context."""
    
    def __init__(self, working_dir: Path) -> None:
        self.working_dir = working_dir
        self.is_git_repo = False
        self.branch: Optional[str] = None
        self._detect_git()
    
    def _detect_git(self) -> None:
        """Detect if working directory is in a git repo."""
        import subprocess
        
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            self.is_git_repo = result.returncode == 0
            
            if self.is_git_repo:
                branch_result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=self.working_dir,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if branch_result.returncode == 0:
                    self.branch = branch_result.stdout.strip() or None
        except Exception:
            self.is_git_repo = False
    
    def get_context(self) -> str:
        """Get git context string for system prompt."""
        if not self.is_git_repo:
            return ""
        
        context = "\nYou are working in a git repository."
        if self.branch:
            context += f" Current branch: `{self.branch}`."
        return context