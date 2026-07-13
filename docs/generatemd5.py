"""
Generate Jekyll/Just-the-Docs markdown pages from your spreadsheet.

Compatible with the new database:
- page_id format: 8 digits + "_" + lang, e.g. 01020000_en
- Uses display_order as nav_order
- Resolves parent + grand_parent titles from parent_id lookup
- NEVER writes parent_id into YAML
- NEVER writes NaN/"nan"/empty keys into YAML

CHANGELOG (this version):
- ADDED: a "Table of Contents" block listing direct child pages, inserted
  ONLY on pages where has_children == True. This is a managed block
  (like the existing EU funding footer) that is safely stripped and
  re-inserted on every run, so it never duplicates and never disturbs
  hand-written body content.
- Everything else is unchanged from the previous version.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml


# ---------------------------
# CONFIG (paths are script-relative)
# ---------------------------
BASE_DIR = Path(__file__).resolve().parent  # .../docs
EXCEL_PATH = BASE_DIR / "iNUXHandbook.xlsx"
OUTPUT_DIR = BASE_DIR / "generated"        # i.e., docs/generated/

WELCOME_PAGE_ID = "00000000_en"

# ---------------------------
# Helpers
# ---------------------------

def is_missing(value: Any) -> bool:
    """True for None, NaN, '', 'nan', 'NaN', etc."""
    if value is None:
        return True
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
    Hook to normalize nav titles if needed.
    Keep minimal; extend later if you introduce special labels.
    """
    if not title:
        return title
    t = title.strip()
    # historical mapping support (keep if you still use it anywhere)
    if t == "00 Welcome":
        return "Welcome"
    return t


def safe_frontmatter_dump(frontmatter: Dict[str, Any]) -> str:
    """Dump YAML safely with unicode and without reordering keys."""
    return "---\n" + yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True) + "---\n\n"


import re

FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)

def split_frontmatter(md_text: str) -> tuple[str, str]:
    """
    Returns (frontmatter_block_or_empty, rest_of_file).
    If no front matter is found, frontmatter_block is "" and rest is original text.
    """
    m = FRONTMATTER_RE.match(md_text)
    if not m:
        return "", md_text
    return m.group(0), md_text[m.end():]


def upsert_markdown_file(path, new_frontmatter_block: str, new_body_stub: str, toc_md: str = "") -> bool:
    """
    Writes/updates markdown at `path`.
    - If file exists: replaces front matter only, preserves rest,
      AND ensures the managed blocks (child TOC, then EU footer) are
      present at the end, in that order.
    - If file doesn't exist: writes front matter + stub body + managed blocks.
    Returns True if file was written/updated.
    """
    if path.exists():
        old = path.read_text(encoding="utf-8")
        _, rest = split_frontmatter(old)

        # Preserve body, but ensure managed blocks exist at the end
        rest = ensure_managed_blocks_at_end(rest, toc_md)

        path.write_text(new_frontmatter_block + rest, encoding="utf-8")
        return True
    else:
        body = ensure_managed_blocks_at_end(new_body_stub, toc_md)
        path.write_text(new_frontmatter_block + body, encoding="utf-8")
        return True



# ---------------------------
# EU co-funding block (footer-style, auto-replaces old versions)
# ---------------------------

import re

EU_BLOCK_MARKER = "<!-- EU_FUNDING_FOOTER -->"

EU_FUNDING_BLOCK = r"""
<!-- EU_FUNDING_FOOTER -->
<hr style="margin:0.4rem 0;">

<div style="
  display:flex;
  align-items:center;
  gap:0.75rem;
  font-size:0.6rem;
  line-height:1.35;
">
  <div style="flex:0 0 160px; text-align:center;">
    <img src='{{ "/assets/images/eu-funded.jpg" | relative_url }}'
         alt="Co-funded by the European Union"
         style="max-width:160px; height:auto;">
  </div>
  <div style="flex:1; text-align:justify; hyphens:auto;">
    This project is co-funded by the European Union. However, the views and opinions
    expressed are solely those of the author(s) and do not necessarily reflect those
    of the European Union or the National Agency DAAD. Neither the European Union nor
    the granting authority can be held responsible for them.
  </div>
</div>
""".strip() + "\n"



# Remove old/new EU blocks (anywhere), then append the new one at the end.
EU_BLOCK_REMOVE_RE = re.compile(
    r"""
    # Remove EU footer variants only if they sit at the very end of the file
    (?:\n{0,2}(?:---\s*\n{0,2})?)?                 # optional markdown hr before
    (?:\s*<hr\b[^>]*>\s*)?                        # optional html hr before
    \s*
    (?:<!--\s*EU_FUNDING_FOOTER\s*-->.*?)(?=\Z)    # marker-based footer (any content) at end
    |
    (?:\n{0,2}(?:---\s*\n{0,2})?)?
    (?:\s*<hr\b[^>]*>\s*)?
    \s*
    <table\b.*?eu-funded\.jpg.*?</table>\s*(?=\Z)  # old table version at end
    |
    (?:\n{0,2}(?:---\s*\n{0,2})?)?
    (?:\s*<hr\b[^>]*>\s*)?
    \s*
    <div\b.*?eu-funded\.jpg.*?</div>\s*(?=\Z)      # older div version at end
    """,
    flags=re.IGNORECASE | re.DOTALL | re.VERBOSE,
)


def strip_eu_block_at_end(md_body: str) -> str:
    """Remove any EU block variant if it sits at the end. Pure helper (no re-append)."""
    body = md_body.rstrip()
    body = re.sub(EU_BLOCK_REMOVE_RE, "", body).rstrip()
    return body


def ensure_eu_block_at_end(md_body: str) -> str:
    """
    Always enforce the *new footer-style* EU block at the end.
    Kept for backward compatibility (used if called directly elsewhere).
    """
    body = strip_eu_block_at_end(md_body)
    body = body + "\n\n" + EU_FUNDING_BLOCK
    return body


# ---------------------------
# NEW: Child-pages Table of Contents (managed block)
# ---------------------------
# Inserted ONLY for pages with has_children == True.
# Sits between the (preserved) hand-written body and the EU footer.
# Safely stripped and re-inserted on every run, same pattern as the EU block.

TOC_BLOCK_MARKER = "<!-- CHILD_TOC -->"

TOC_BLOCK_REMOVE_RE = re.compile(
    r"""
    (?:\n{0,2}(?:---\s*\n{0,2})?)?         # optional markdown hr before
    \s*
    <!--\s*CHILD_TOC\s*-->.*?(?=\Z)        # marker-based TOC block, to end of string
    """,
    flags=re.IGNORECASE | re.DOTALL | re.VERBOSE,
)


def strip_toc_block_at_end(md_body: str) -> str:
    """Remove a previously-inserted child TOC block if present at the end."""
    body = md_body.rstrip()
    body = re.sub(TOC_BLOCK_REMOVE_RE, "", body).rstrip()
    return body


def build_child_toc_block(children: List[Dict[str, str]]) -> str:
    """
    children: list of {"title": ..., "page_id": ...} for direct children,
    already in display order.
    Returns the full managed TOC markdown block (with marker), or "" if
    there are no children to list.
    """
    if not children:
        return ""

    lines = [TOC_BLOCK_MARKER, "", "---", "", "## Table of Contents", ""]
    for child in children:
        title = child["title"]
        page_id = child["page_id"]
        lines.append(f"- [{title}]({page_id}.html)")

    return "\n".join(lines) + "\n"


def ensure_managed_blocks_at_end(md_body: str, toc_md: str = "") -> str:
    """
    Enforces, in order, at the very end of the body:
      1) preserved hand-written content (untouched)
      2) child TOC block (only if toc_md is non-empty)
      3) EU funding footer (always)

    Old instances of either managed block (in any order/position at the
    end) are stripped first so re-running the generator never duplicates
    them.
    """
    body = md_body

    # Strip both managed blocks if present at the end, in either order,
    # repeating until stable (handles TOC-then-EU or EU-then-TOC cases).
    prev = None
    while prev != body:
        prev = body
        body = strip_eu_block_at_end(body)
        body = strip_toc_block_at_end(body)

    if toc_md:
        body = body.rstrip() + "\n\n" + toc_md

    body = body.rstrip() + "\n\n" + EU_FUNDING_BLOCK
    return body


# ---------------------------
# Markdown generation
# ---------------------------
def build_frontmatter(
    *,
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
        parent_title = normalize_nav_title(title_by_page_id.get(parent_id, ""))
        if parent_title:
            fm["parent"] = parent_title

            gp_id = clean_str(parent_by_page_id.get(parent_id, ""), "")
            if gp_id:
                gp_title = normalize_nav_title(title_by_page_id.get(gp_id, ""))
                if gp_title:
                    fm["grand_parent"] = gp_title

    return fm


def build_body(*, page_id: str, parent_id: str, lang_code: str, title: str) -> str:
    meta = (
        f"<!-- page_id: {page_id} -->\n"
        f"<!-- parent_id: {parent_id} -->\n"
        f"<!-- lang_code: {lang_code} -->\n\n"
    )
    return meta + f"# {title}\n\n"


# ---------------------------
# Main
# ---------------------------
def main() -> None:
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Excel file not found: {EXCEL_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Read everything as string to avoid pandas turning blanks into NaN surprises.
    df = pd.read_excel(EXCEL_PATH, dtype=str).fillna("")

    # Required columns in your new sheet
    required_cols = {"page_id", "title"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise KeyError(f"Missing required columns in Excel: {sorted(missing_cols)}")

    # Normalize key columns
    df["page_id"] = df["page_id"].astype(str).str.strip()
    df["title"] = df["title"].astype(str).str.strip()

    # Lookups
    title_by_page_id: Dict[str, str] = dict(zip(df["page_id"], df["title"]))

    parent_by_page_id: Dict[str, str] = {}
    if "parent_id" in df.columns:
        parent_by_page_id = dict(zip(df["page_id"], df["parent_id"].astype(str).str.strip()))

    # --- NEW: build children_by_parent_id for the child TOC feature ---
    # Sort by sort_key if available (matches the spreadsheet's intended
    # ordering), falling back to display_order, falling back to page_id.
    has_sort_key = "sort_key" in df.columns
    has_display_order = "display_order" in df.columns

    def sort_value(row) -> tuple:
        if has_sort_key and not is_missing(row.get("sort_key")):
            try:
                return (0, float(row.get("sort_key")))
            except Exception:
                pass
        if has_display_order:
            return (1, as_int(row.get("display_order"), default=0))
        return (2, str(row.get("page_id")))

    children_by_parent_id: Dict[str, List[Dict[str, str]]] = {}
    if "parent_id" in df.columns:
        rows_sorted = sorted(df.to_dict("records"), key=sort_value)
        for row in rows_sorted:
            pid = clean_str(row.get("parent_id"), "")
            cid = clean_str(row.get("page_id"), "")
            ctitle = clean_str(row.get("title"), cid)
            if pid and cid:
                children_by_parent_id.setdefault(pid, []).append(
                    {"title": ctitle, "page_id": cid}
                )

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

        # Use display_order as nav_order (your new sheet standard)
        nav_order = as_int(row.get("display_order", 0), default=0)
        if nav_order <= 0:
            nav_order = 1  # deterministic fallback

        frontmatter = build_frontmatter(
            title=title,
            layout=layout,
            nav_order=nav_order,
            has_children=has_children,
            parent_id=parent_id,
            title_by_page_id=title_by_page_id,
            parent_by_page_id=parent_by_page_id,
        )

        front = safe_frontmatter_dump(frontmatter)
        stub_body = build_body(page_id=page_id, parent_id=parent_id, lang_code=lang_code, title=title)

        # --- NEW: only build a TOC block for pages that actually have children ---
        toc_md = ""
        if has_children:
            children = children_by_parent_id.get(page_id, [])
            toc_md = build_child_toc_block(children)

        out_path = OUTPUT_DIR / f"{page_id}.md"

        upsert_markdown_file(out_path, front, stub_body, toc_md=toc_md)

        wrote += 1

    print(f"✅ Generated {wrote} pages in: {OUTPUT_DIR}")
    print(f"↪ Skipped {skipped} welcome/root rows (page_id={WELCOME_PAGE_ID})")
    print(f"📄 Source spreadsheet: {EXCEL_PATH}")

if __name__ == "__main__":
    main()
