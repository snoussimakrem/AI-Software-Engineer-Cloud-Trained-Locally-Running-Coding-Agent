import os
import fnmatch


class FileTools:
    """
    Restricted filesystem tools scoped to a single working directory.
    The agent cannot read/write outside this root — this is the
    boundary we enforce BEFORE ever giving terminal access (Phase 6).
    """

    def __init__(self, root: str):
        self.root = os.path.abspath(root)

    def _resolve(self, path: str) -> str:
        full = os.path.abspath(os.path.join(self.root, path))
        if not full.startswith(self.root):
            raise PermissionError(f"Path '{path}' escapes the allowed working directory")
        return full

    def list_files(self, subdir: str = ".") -> list[str]:
        target = self._resolve(subdir)
        results = []
        for dirpath, dirnames, filenames in os.walk(target):
            dirnames[:] = [d for d in dirnames if d != ".git"]
            for f in filenames:
                rel = os.path.relpath(os.path.join(dirpath, f), self.root)
                results.append(rel)
        return sorted(results)

    def read_file(self, path: str) -> str:
        full = self._resolve(path)
        with open(full, "r") as f:
            return f.read()

    def search_code(self, pattern: str) -> list[str]:
        matches = []
        for rel_path in self.list_files():
            full = os.path.join(self.root, rel_path)
            try:
                with open(full, "r") as f:
                    for lineno, line in enumerate(f, start=1):
                        if fnmatch.fnmatch(line, f"*{pattern}*"):
                            matches.append(f"{rel_path}:{lineno}: {line.strip()}")
            except (UnicodeDecodeError, IsADirectoryError):
                continue
        return matches

    def write_file(self, path: str, content: str) -> str:
        full = self._resolve(path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)
        return f"Wrote {len(content)} bytes to {path}"

    def edit_file(self, path: str, old_text: str, new_text: str) -> str:
        full = self._resolve(path)
        with open(full, "r") as f:
            content = f.read()
        if old_text not in content:
            raise ValueError(f"old_text not found in {path}")
        content = content.replace(old_text, new_text, 1)
        with open(full, "w") as f:
            f.write(content)
        return f"Edited {path}"
