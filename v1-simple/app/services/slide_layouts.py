"""Slide layout definitions for the LMS slide editor."""

LAYOUTS = {
    "single-column": {
        "rows": 1,
        "cols": 12,
        "regions": [{"col": 1, "span": 12}],
    },
    "two-column": {
        "rows": 1,
        "cols": 12,
        "regions": [{"col": 1, "span": 6}, {"col": 7, "span": 6}],
    },
    "title-content": {
        "rows": 2,
        "cols": 12,
        "regions": [
            {"row": 1, "col": 1, "span": 12},
            {"row": 2, "col": 1, "span": 12},
        ],
    },
    "image-left": {
        "rows": 1,
        "cols": 12,
        "regions": [
            {"col": 1, "span": 5, "type": "image"},
            {"col": 6, "span": 7},
        ],
    },
    "image-right": {
        "rows": 1,
        "cols": 12,
        "regions": [
            {"col": 1, "span": 7},
            {"col": 8, "span": 5, "type": "image"},
        ],
    },
    "centered": {
        "rows": 1,
        "cols": 12,
        "regions": [{"col": 3, "span": 8}],
    },
    "quiz": {
        "rows": 1,
        "cols": 12,
        "regions": [{"col": 2, "span": 10, "type": "assessment"}],
    },
}

VALID_LAYOUTS = set(LAYOUTS.keys())
