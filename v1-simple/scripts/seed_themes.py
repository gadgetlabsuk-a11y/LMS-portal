"""Seed the 5 starter themes into the database.

Run once after applying migrations:
    python scripts/seed_themes.py
"""

import sys
import os

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import Theme

# ---------------------------------------------------------------------------
# Starter theme definitions
# ---------------------------------------------------------------------------

STARTER_THEMES = [
    {
        "slug": "corporate",
        "name": "Corporate",
        "is_system": True,
        "tokens": {
            "colors": {
                "primary": "#1F3A5F",
                "secondary": "#6366F1",
                "accent": "#F59E0B",
                "bg": "#FFFFFF",
                "text": "#1F2937",
                "muted": "#6B7280",
                "success": "#10B981",
                "warning": "#F59E0B",
                "error": "#EF4444",
            },
            "typography": {
                "body_family": "Inter, system-ui, sans-serif",
                "heading_family": "Poppins, system-ui, sans-serif",
                "scale": {"h1": 32, "h2": 24, "h3": 20, "body": 16, "small": 14},
                "line_height": 1.5,
            },
            "spacing": {"unit": 8, "slide_padding": 48},
            "radius": {"sm": 4, "md": 8, "lg": 16},
            "buttons": {"style": "rounded", "weight": 500},
            "shadows": {
                "sm": "0 1px 2px rgba(0,0,0,0.05)",
                "md": "0 4px 6px rgba(0,0,0,0.1)",
            },
        },
    },
    {
        "slug": "modern",
        "name": "Modern",
        "is_system": True,
        "tokens": {
            "colors": {
                "primary": "#7C3AED",
                "secondary": "#EC4899",
                "accent": "#F59E0B",
                "bg": "#FFFFFF",
                "text": "#1F2937",
                "muted": "#6B7280",
                "success": "#10B981",
                "warning": "#F59E0B",
                "error": "#EF4444",
            },
            "typography": {
                "body_family": "Inter, system-ui, sans-serif",
                "heading_family": "Poppins, system-ui, sans-serif",
                "scale": {"h1": 40, "h2": 30, "h3": 22, "body": 16, "small": 14},
                "line_height": 1.6,
            },
            "spacing": {"unit": 8, "slide_padding": 48},
            "radius": {"sm": 8, "md": 16, "lg": 24},
            "buttons": {"style": "rounded", "weight": 600},
            "shadows": {
                "sm": "0 1px 3px rgba(0,0,0,0.1)",
                "md": "0 4px 12px rgba(0,0,0,0.15)",
            },
        },
    },
    {
        "slug": "minimal",
        "name": "Minimal",
        "is_system": True,
        "tokens": {
            "colors": {
                "primary": "#000000",
                "secondary": "#000000",
                "accent": "#000000",
                "bg": "#FFFFFF",
                "text": "#000000",
                "muted": "#6B7280",
                "success": "#000000",
                "warning": "#000000",
                "error": "#000000",
            },
            "typography": {
                "body_family": "Inter, system-ui, sans-serif",
                "heading_family": "JetBrains Mono, monospace",
                "scale": {"h1": 32, "h2": 24, "h3": 20, "body": 16, "small": 14},
                "line_height": 1.5,
            },
            "spacing": {"unit": 8, "slide_padding": 48},
            "radius": {"sm": 0, "md": 0, "lg": 0},
            "buttons": {"style": "square", "weight": 400},
            "shadows": {"sm": "none", "md": "none"},
        },
    },
    {
        "slug": "compliance",
        "name": "Compliance",
        "is_system": True,
        "tokens": {
            "colors": {
                "primary": "#000000",
                "secondary": "#374151",
                "accent": "#1F3A5F",
                "bg": "#FFFFFF",
                "text": "#000000",
                "muted": "#4B5563",
                "success": "#10B981",
                "warning": "#F59E0B",
                "error": "#EF4444",
            },
            "typography": {
                "body_family": "Atkinson Hyperlegible, sans-serif",
                "heading_family": "Atkinson Hyperlegible, sans-serif",
                "scale": {"h1": 28, "h2": 22, "h3": 18, "body": 16, "small": 14},
                "line_height": 1.6,
            },
            "spacing": {"unit": 6, "slide_padding": 32},
            "radius": {"sm": 2, "md": 4, "lg": 8},
            "buttons": {"style": "rounded", "weight": 500},
            "shadows": {"sm": "none", "md": "none"},
        },
    },
    {
        "slug": "branded",
        "name": "Branded",
        "is_system": True,
        "tokens": {
            "colors": {
                "primary": "#374151",
                "secondary": "#6B7280",
                "accent": "#9CA3AF",
                "bg": "#FFFFFF",
                "text": "#1F2937",
                "muted": "#6B7280",
                "success": "#10B981",
                "warning": "#F59E0B",
                "error": "#EF4444",
            },
            "typography": {
                "body_family": "Inter, system-ui, sans-serif",
                "heading_family": "Inter, system-ui, sans-serif",
                "scale": {"h1": 32, "h2": 24, "h3": 20, "body": 16, "small": 14},
                "line_height": 1.5,
            },
            "spacing": {"unit": 8, "slide_padding": 48},
            "radius": {"sm": 4, "md": 8, "lg": 16},
            "buttons": {"style": "rounded", "weight": 500},
            "shadows": {
                "sm": "0 1px 2px rgba(0,0,0,0.05)",
                "md": "0 4px 6px rgba(0,0,0,0.1)",
            },
        },
    },
]


def seed(database_url: str | None = None) -> None:
    if database_url is None:
        # Try to pull from environment / app config
        try:
            from app.config import settings
            database_url = str(settings.database_url).replace("+aiosqlite", "").replace("+asyncpg", "")
        except Exception:
            # Fallback to local SQLite
            database_url = "sqlite:///./data/lms.db"

    engine = create_engine(database_url, echo=False)

    with Session(engine) as session:
        inserted = 0
        updated = 0
        for theme_data in STARTER_THEMES:
            existing = session.scalar(select(Theme).where(Theme.slug == theme_data["slug"]))
            if existing is None:
                session.add(Theme(**theme_data))
                inserted += 1
            else:
                # Update tokens in case they changed
                existing.tokens = theme_data["tokens"]
                existing.name = theme_data["name"]
                updated += 1
        session.commit()

    print(f"Themes seeded — {inserted} inserted, {updated} updated.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed starter themes")
    parser.add_argument("--db", default=None, help="SQLAlchemy database URL (sync driver)")
    args = parser.parse_args()

    seed(args.db)
