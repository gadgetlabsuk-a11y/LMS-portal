"""Block validation logic for the LMS slide editor."""

VALID_BLOCK_TYPES = {
    "heading", "paragraph", "image", "video", "audio",
    "divider", "spacer", "bullets", "accordion", "button",
    "mcq_single", "mcq_multi", "tf",
}


def validate_block(block: dict) -> None:
    """Validate a single block. Raises ValueError on violation."""
    block_type = block.get("type")

    if block_type not in VALID_BLOCK_TYPES:
        raise ValueError(f"Unknown block type: {block_type!r}")

    props = block.get("props", {})

    if block_type == "image":
        alt = props.get("alt", "")
        if not isinstance(alt, str) or not alt.strip():
            raise ValueError("image block: props.alt must be a non-empty string")

    elif block_type == "audio":
        transcript = props.get("transcript", "")
        if not isinstance(transcript, str) or not transcript.strip():
            raise ValueError("audio block: props.transcript must be a non-empty string")

    elif block_type == "video":
        transcript = props.get("transcript", "")
        if not isinstance(transcript, str) or not transcript.strip():
            raise ValueError(
                "video block: props.transcript is required and must be a non-empty string (WCAG)"
            )

    elif block_type == "mcq_single":
        options = props.get("options", [])
        correct_count = sum(1 for opt in options if opt.get("correct") is True)
        if correct_count != 1:
            raise ValueError(
                f"mcq_single block: exactly 1 option must have correct=True, got {correct_count}"
            )

    elif block_type == "mcq_multi":
        options = props.get("options", [])
        correct_count = sum(1 for opt in options if opt.get("correct") is True)
        if correct_count < 1:
            raise ValueError(
                "mcq_multi block: at least 1 option must have correct=True"
            )

    elif block_type == "tf":
        correct_answer = props.get("correct_answer")
        if not isinstance(correct_answer, bool):
            raise ValueError(
                f"tf block: props.correct_answer must be a boolean, got {correct_answer!r}"
            )


def validate_blocks(blocks: list[dict]) -> None:
    """Validate all blocks in a slide, including layout overlap check."""
    for block in blocks:
        validate_block(block)
    _check_layout_overlaps(blocks)


def _check_layout_overlaps(blocks: list[dict]) -> None:
    """Raise ValueError if any two blocks occupy the same grid cell."""
    occupied: set[tuple[int, int]] = set()

    for block in blocks:
        layout = block.get("layout", {})
        col_start = layout.get("col_start", 1)
        col_span = layout.get("col_span", 1)
        row_start = layout.get("row_start", 1)
        row_span = layout.get("row_span", 1)

        for row in range(row_start, row_start + row_span):
            for col in range(col_start, col_start + col_span):
                cell = (row, col)
                if cell in occupied:
                    raise ValueError(
                        f"Layout overlap detected at row={row}, col={col} "
                        f"(block id={block.get('id')!r})"
                    )
                occupied.add(cell)
