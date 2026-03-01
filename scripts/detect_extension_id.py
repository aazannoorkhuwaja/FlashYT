import argparse
import json
import os
import sys
from typing import Dict, Iterable, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from constants import EXTENSION_NAME, EXTENSION_NAME_ALIASES


TARGET_NAMES = {EXTENSION_NAME.lower(), *(name.lower() for name in EXTENSION_NAME_ALIASES)}


def _is_valid_extension_id(value: str) -> bool:
    return len(value) == 32 and all("a" <= ch <= "p" for ch in value)


def _candidate_user_data_roots() -> List[str]:
    roots: List[str] = []
    if sys.platform == "win32":
        appdata = os.environ.get("LOCALAPPDATA", "")
        if appdata:
            roots.extend(
                [
                    os.path.join(appdata, "Google", "Chrome", "User Data"),
                    os.path.join(appdata, "BraveSoftware", "Brave-Browser", "User Data"),
                    os.path.join(appdata, "Microsoft", "Edge", "User Data"),
                    os.path.join(appdata, "Chromium", "User Data"),
                ]
            )
    elif sys.platform == "darwin":
        appdata = os.path.expanduser("~/Library/Application Support")
        roots.extend(
            [
                os.path.join(appdata, "Google", "Chrome"),
                os.path.join(appdata, "BraveSoftware", "Brave-Browser"),
                os.path.join(appdata, "Microsoft Edge"),
                os.path.join(appdata, "Chromium"),
            ]
        )
    else:
        home = os.path.expanduser("~")
        roots.extend(
            [
                os.path.join(home, ".config", "google-chrome"),
                os.path.join(home, ".config", "chromium"),
                os.path.join(home, ".config", "BraveSoftware", "Brave-Browser"),
                os.path.join(home, ".config", "microsoft-edge"),
                # Snap-packaged browsers (Ubuntu 22+/24+)
                os.path.join(home, "snap", "chromium", "current", ".config", "chromium"),
                os.path.join(home, "snap", "brave", "current", ".config", "BraveSoftware", "Brave-Browser"),
                os.path.join(home, "snap", "chromium", "common", ".config", "chromium"),
                # Flatpak-packaged browsers
                os.path.join(home, ".var", "app", "com.google.Chrome", "config", "google-chrome"),
                os.path.join(home, ".var", "app", "com.brave.Browser", "config", "BraveSoftware", "Brave-Browser"),
                os.path.join(home, ".var", "app", "org.chromium.Chromium", "config", "chromium"),
            ]
        )
    return roots


def _iter_profile_dirs() -> Iterable[str]:
    for root in _candidate_user_data_roots():
        if not os.path.isdir(root):
            continue
        try:
            profile_nodes = os.listdir(root)
        except Exception:
            continue
        for node in profile_nodes:
            profile_dir = os.path.join(root, node)
            if os.path.isdir(profile_dir):
                yield profile_dir


def _read_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _manifest_name_matches(manifest_path: str) -> bool:
    manifest = _read_json(manifest_path)
    if not manifest:
        return False
    name = (manifest.get("name") or "").strip().lower()
    return name in TARGET_NAMES


def _score_and_record(candidates: Dict[str, int], ext_id: str, score: int) -> None:
    if not _is_valid_extension_id(ext_id):
        return
    candidates[ext_id] = max(candidates.get(ext_id, 0), score)


def _collect_from_extension_folders(profile_dir: str, candidates: Dict[str, int]) -> None:
    ext_dir = os.path.join(profile_dir, "Extensions")
    if not os.path.isdir(ext_dir):
        return
    try:
        ext_ids = os.listdir(ext_dir)
    except Exception:
        return

    for ext_id in ext_ids:
        if not _is_valid_extension_id(ext_id):
            continue
        ext_root = os.path.join(ext_dir, ext_id)
        if not os.path.isdir(ext_root):
            continue
        try:
            versions = sorted(os.listdir(ext_root), reverse=True)
        except Exception:
            continue
        for version in versions:
            manifest_path = os.path.join(ext_root, version, "manifest.json")
            if os.path.isfile(manifest_path) and _manifest_name_matches(manifest_path):
                _score_and_record(candidates, ext_id, 80)
                break


def _matches_preferences_entry(entry: dict) -> bool:
    manifest = entry.get("manifest") or {}
    name = (manifest.get("name") or "").strip().lower()
    if name in TARGET_NAMES:
        return True

    unpacked_path = entry.get("path")
    if unpacked_path:
        manifest_path = os.path.join(unpacked_path, "manifest.json")
        if os.path.isfile(manifest_path) and _manifest_name_matches(manifest_path):
            return True

    return False


def _collect_from_preferences(profile_dir: str, candidates: Dict[str, int]) -> None:
    pref_path = os.path.join(profile_dir, "Preferences")
    pref_data = _read_json(pref_path)
    if not pref_data:
        return

    settings = ((pref_data.get("extensions") or {}).get("settings") or {})
    if not isinstance(settings, dict):
        return

    for ext_id, entry in settings.items():
        if not isinstance(entry, dict):
            continue
        if not _is_valid_extension_id(ext_id):
            continue
        if not _matches_preferences_entry(entry):
            continue
        # Preferences are a stronger signal for active unpacked installs.
        state = 1 if entry.get("state") == 1 else 0
        _score_and_record(candidates, ext_id, 100 + state)


def find_extension_ids() -> List[str]:
    candidates: Dict[str, int] = {}
    for profile_dir in _iter_profile_dirs():
        _collect_from_extension_folders(profile_dir, candidates)
        _collect_from_preferences(profile_dir, candidates)
    # Highest confidence first, then deterministic ID order.
    sorted_ids = sorted(candidates.items(), key=lambda item: (-item[1], item[0]))
    return [ext_id for ext_id, _ in sorted_ids]


def find_extension_id() -> Optional[str]:
    ids = find_extension_ids()
    return ids[0] if ids else None


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--all", action="store_true", help="Print all matching extension IDs, one per line")
    parser.add_argument("--all-csv", action="store_true", help="Print all matching extension IDs as CSV")
    args = parser.parse_args()

    ids = find_extension_ids()
    if not ids:
        return 1

    if args.all_csv:
        sys.stdout.write(",".join(ids))
        return 0

    if args.all:
        sys.stdout.write("\n".join(ids))
        return 0

    # Default behavior kept for backward compatibility.
    sys.stdout.write(ids[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
