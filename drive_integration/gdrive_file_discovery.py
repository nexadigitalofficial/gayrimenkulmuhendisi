# -*- coding: utf-8 -*-
"""
gdrive_file_discovery.py — Recursive File Discovery, Metadata Extraction & Change Tracking
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging = __import__("logging").getLogger("nexa.drive.discovery")


class DriveFileDiscovery:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or (Path(__file__).resolve().parent.parent / "static" / "projeler")

    def discover_all_files(self, recursive: bool = True) -> List[Dict[str, Any]]:
        results = []
        if not self.root_dir.exists():
            return results

        pattern = "**/*.*" if recursive else "*.*"
        for p in self.root_dir.glob(pattern):
            if p.is_file():
                stat = p.stat()
                results.append({
                    "name": p.name,
                    "path": str(p),
                    "extension": p.suffix.lower(),
                    "size_bytes": stat.st_size,
                    "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "folder": p.parent.name
                })
        return results

    def calculate_file_hash(self, path: Path) -> str:
        hasher = hashlib.md5()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""


class DuplicateDetector:
    @staticmethod
    def detect_duplicates(file_list: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        seen_names = {}
        duplicates = {}
        for f in file_list:
            name = f.get("name", "")
            if name in seen_names:
                if name not in duplicates:
                    duplicates[name] = [seen_names[name]]
                duplicates[name].append(f.get("path", ""))
            else:
                seen_names[name] = f.get("path", "")
        return duplicates


class ChangeTracker:
    def __init__(self, state_file: Optional[Path] = None):
        self.state_file = state_file or (Path(__file__).resolve().parent.parent / "static" / "data" / "watch_state.json")

    def detect_changes(self, current_snapshot: Dict[str, float]) -> List[str]:
        if not self.state_file.exists():
            return list(current_snapshot.keys())
        try:
            prev = json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            prev = {}

        changed = []
        for k, v in current_snapshot.items():
            if prev.get(k) != v:
                changed.append(k)
        return changed
