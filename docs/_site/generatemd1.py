"""
Generate Jekyll/Just-the-Docs markdown pages from iNUXHandbook.xlsx.

Key behaviors:
- Reads iNUXHandbook.xlsx
- Writes docs/generated/<page_id>.md
- Skips welcome/root row page_id == 000000_en
- YAML uses Just-the-Docs: parent + grand_parent (resolved from parent_id via title lookup)
- NEVER writes parent_id into YAML
- NEVER writes NaN/"nan"/empty keys into YAML
- YAML serialization is safe for special characters via yaml.safe_dump()
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import yaml


# ---------------------------
# CONFIG (paths are script-relative)
# ---------------------------
BASE_DIR = Path(__file__).resolve().parent  # .../docs
EXCEL_PATH = BASE_DIR / "iNUXHandbook.xlsx"
OUTPUT_DIR = BASE_DIR / "generated"        # i.e., docs/generated/

WELCOME_PAGE_ID = "000000_en"


# ---------------------------
# Helpers
# ---------------------------
def is_missing(value: Any) -> bool:
    """True for None, NaN, '', 'nan', 'NaN', etc."""
    if value is None:
        return True
    # pandas NaN
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    s = str(value).strip()
    return s == "" or s.lower() == "nan"


def clean_str(value: Any, default: str = "") -> str:
    return default if is_missing(value) else str(value).strip()


def as_bool(value: Any) -> bool:
    """Robust bool parsing for spreadsheet values."""
    if isinstance(value, bool):
        return value
    if is_missing(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y", "on"}


def as_int(value: Any, default: int = 0) -> int:
    if is_missing(value):
        return default
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default


def normalize_nav_title(title: Optional[str]) -> Optional[str]:
    """
    Keep this hook to match your existing generator.
    Currently only maps '00 Welcome' -> 'Welcome'.
    Extend if needed.
    """
    if not title:
        return title
    t = title.strip()
    if t == "00 Welcome":
        return "Welcome"
    return t


def safe_frontmatter_dump(frontmatter: Dict[str, Any]) -> str:
    """
    Dump YAML safely with unicode and without reordering keys.
    """
    return "---\n" + yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True) + "---\n\n"


# ---------------------------
# Markdown generation
# ---------------------------
def build_frontmatter(
    page_id: str,
    title: str,
    layout: str,
    nav_order: int,
    has_children: bool,
    parent_id: str,
    title_by_page_id: Dict[str, str],
    parent_by_page_id: Dict[str, str],
) -> Dict[str, Any]:
    fm: Dict[str, Any] = {
        "title": title,
        "layout": layout,
        "nav_order": nav_order,
        "has_children": has_children,
    }

    # Like your generator: disable theme TOC when page has children
    if has_children:
        fm["has_toc"] = False

    # Resolve parent/grand_parent titles from IDs
    if parent_id:
        parent_title = title_by_page_id.get(parent_id, "")
        parent_title = normalize_nav_title(parent_title) if parent_title else ""

        if parent_title:
            fm["parent"] = parent_title

            gp_id = parent_by_page_id.get(parent_id, "")
            gp_id = clean_str(gp_id, "")
            if gp_id:
                gp_title = title_by_page_id.get(gp_id, "")
                gp_title = normalize_nav_title(gp_title) if gp_title else ""
                if gp_title:
                    fm["grand_parent"] = gp_title

    return fm


def build_body(page_id: str, parent_id: str, lang_code: str, title: str, description: str) -> str:
    meta = (
        f"<!-- page_id: {page_id} -->\n"
        f"<!-- parent_id: {parent_id} -->\n"
        f"<!-- lang_code: {lang_code} -->\n\n"
    )

    # Minimal body; you can change this later
    body = f"# {title}\n\n"
    if description:
        body += f"{description}\n\n"

    return meta + body


# ---------------------------
# Main
# ---------------------------
def main() -> None:
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Excel file not found: {EXCEL_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Read everything as string to avoid pandas turning blanks into NaN surprises.
    df = pd.read_excel(EXCEL_PATH, dtype=str).fillna("")

    # Basic required columns check
    required_cols = {"page_id", "title"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise KeyError(f"Missing required columns in Excel: {sorted(missing_cols)}")

    # Build lookup maps
    # (strip to avoid invisible mismatch)
    df["page_id"] = df["page_id"].astype(str).str.strip()
    df["title"] = df["title"].astype(str).str.strip()

    title_by_page_id: Dict[str, str] = dict(zip(df["page_id"], df["title"]))
    parent_by_page_id: Dict[str, str] = {}
    if "parent_id" in df.columns:
        parent_by_page_id = dict(zip(df["page_id"], df["parent_id"].astype(str).str.strip()))

    wrote = 0
    skipped = 0

    for _, row in df.iterrows():
        page_id = clean_str(row.get("page_id"), "")
        if not page_id:
            continue

        # Skip welcome/root
        if page_id == WELCOME_PAGE_ID:
            skipped += 1
            continue

        title = clean_str(row.get("title"), page_id)
        layout = clean_str(row.get("layout"), "home")
        lang_code = clean_str(row.get("lang_code"), "en")

        parent_id = clean_str(row.get("parent_id"), "") if "parent_id" in df.columns else ""

        has_children = as_bool(row.get("has_children", False))

        nav_order = as_int(row.get("display_order", 0), default=0)
        if nav_order <= 0:
            # fallback: keep deterministic ordering even if display_order missing
            nav_order = 1

        description = ""
        if "description" in df.columns:
            description = clean_str(row.get("description"), "")

        frontmatter = build_frontmatter(
            page_id=page_id,
            title=title,
            layout=layout,
            nav_order=nav_order,
            has_children=has_children,
            parent_id=parent_id,
            title_by_page_id=title_by_page_id,
            parent_by_page_id=parent_by_page_id,
        )

        md = safe_frontmatter_dump(frontmatter) + build_body(
            page_id=page_id,
            parent_id=parent_id,
            lang_code=lang_code,
            title=title,
            description=description,
        )

        out_path = OUTPUT_DIR / f"{page_id}.md"
        out_path.write_text(md, encoding="utf-8")
        wrote += 1

    print(f"✅ Generated {wrote} pages in: {OUTPUT_DIR}")
    print(f"↪ Skipped {skipped} welcome/root rows (page_id={WELCOME_PAGE_ID})")


if __name__ == "__main__":
    main()
