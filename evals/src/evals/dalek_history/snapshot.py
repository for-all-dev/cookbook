"""Codebase snapshot capture for challenge packaging."""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def capture_codebase_snapshot(
    repo_path: Path, relevant_files: set[Path] | None = None
) -> dict[str, str]:
    """Capture content of all relevant Lean files.

    Args:
        repo_path: Path to repository root.
        relevant_files: Set of specific files to include. If None, captures all .lean files.

    Returns:
        Mapping of relative_path -> file_content.
    """
    snapshot = {}

    if relevant_files is None:
        # Capture all .lean files (MVP approach)
        relevant_files = set(repo_path.rglob("*.lean"))

    for file_path in relevant_files:
        if file_path.is_file():
            try:
                # Get relative path from repo root
                rel_path = file_path.relative_to(repo_path)
                content = file_path.read_text(encoding="utf-8")
                snapshot[str(rel_path)] = content
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")

    logger.info(f"Captured snapshot of {len(snapshot)} files")
    return snapshot


def identify_dependencies(repo_path: Path, proof_file: Path) -> set[Path]:
    """Identify transitive dependencies of a proof file by parsing imports.

    This is a simplified implementation that parses import statements.
    A complete implementation would need to:
    1. Parse all imports in the file
    2. Recursively find imports in those files
    3. Handle Mathlib and other external dependencies

    For MVP, we just return all .lean files. This can be optimized later.

    Args:
        repo_path: Path to repository root.
        proof_file: Path to the proof file.

    Returns:
        Set of file paths that are dependencies.
    """
    # MVP: Return all .lean files
    # TODO: Implement proper import-based dependency tracking
    return set(repo_path.rglob("*.lean"))


def extract_imports(file_path: Path) -> list[str]:
    """Extract import statements from a Lean file.

    Args:
        file_path: Path to Lean file.

    Returns:
        List of imported module names.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return []

    # Match "import ModuleName" statements
    imports = re.findall(r"^\s*import\s+([A-Za-z0-9._]+)", content, re.MULTILINE)
    return imports


def module_name_to_path(module_name: str, repo_path: Path) -> Path | None:
    """Convert a Lean module name to a file path.

    Args:
        module_name: Module name (e.g., "Curve25519Dalek.Defs.Edwards.Curve")
        repo_path: Repository root path.

    Returns:
        Path to the .lean file, or None if not found.
    """
    # Convert dots to slashes and add .lean extension
    file_path = repo_path / f"{module_name.replace('.', '/')}.lean"

    if file_path.exists():
        return file_path

    return None
