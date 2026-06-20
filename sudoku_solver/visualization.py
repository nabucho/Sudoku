"""Formatting and progress-board rendering for Sudoku explanations."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from .techniques.common import (
    Elimination,
    ExplanationStep,
    Move,
    TechniqueTiming,
    digits_from_mask,
    elimination_text,
    is_single,
    placement_text,
    rc_to_i,
    single_digit,
    zip_pairs,
)


def move_change_details(move: Move | ExplanationStep) -> List[str]:
    """Return human-readable placement and elimination details for a move."""
    details = [placement_text(placement) for placement in move.placements]
    details.extend(elimination_text(elimination) for elimination in move.eliminations)
    return details


def timing_text(move: Move | ExplanationStep) -> str:
    """Format move timing in milliseconds."""
    return f"{move.timing_ms:.2f} ms"


def compact_move_text(move: Move | ExplanationStep) -> str:
    """Format one move for compact step output."""
    details = move_change_details(move)
    if details:
        return f"{move.technique} [{timing_text(move)}]: {', '.join(details)}"
    return f"{move.summary()} [{timing_text(move)}]"


def detailed_move_text(move: Move | ExplanationStep) -> str:
    """Format one move for detailed step output."""
    details = move_change_details(move)
    if details:
        return f"{move.summary()} [{timing_text(move)}] Changes: {', '.join(details)}"
    return f"{move.summary()} [{timing_text(move)}]"


def plural_technique_name(technique: str) -> str:
    """Return a readable plural label for grouped technique output."""
    if technique.endswith("Single"):
        return f"{technique}s"
    if technique == "Guess":
        return "Guesses"
    if technique.endswith("s"):
        return technique
    return f"{technique}s"


def combine_step_group(technique: str, moves: Sequence[ExplanationStep]) -> ExplanationStep:
    """Combine consecutive explanation steps into one display step."""
    placements = [
        placement
        for move in moves
        for placement in move.placements
    ]
    eliminations = [
        elimination
        for move in moves
        for elimination in move.eliminations
    ]
    changed_cells = {
        cell
        for move in moves
        for cell in move.changed_cells
    }
    cause_cells = {
        cell
        for move in moves
        for cell in move.cause_cells
    }
    details = [placement_text(placement) for placement in placements]
    details.extend(elimination_text(elimination) for elimination in eliminations)
    change_count = len(details)
    noun = "change" if change_count == 1 else "changes"

    combined_move = Move(
        technique=technique,
        difficulty=max(move.difficulty for move in moves),
        reason=f"{change_count} {noun}.",
        placements=placements,
        eliminations=eliminations,
    )
    combined_move.cause_cells = sorted(cause_cells)
    combined_move.timing_ms = sum(move.timing_ms for move in moves)
    after_candidates = moves[-1].after_candidates[:] if moves[-1].after_candidates is not None else None
    return ExplanationStep(combined_move, after_candidates, sorted(changed_cells))


def steps_for_style(steps: Sequence[ExplanationStep], style: str) -> List[ExplanationStep]:
    """Return steps transformed according to a CLI step style."""
    if style == "detailed":
        return list[ExplanationStep](steps)

    formatted: List[ExplanationStep] = []
    i = 0
    while i < len(steps):
        current = steps[i]

        if style == "grouped" and current.technique == "Naked Single":
            group = [current]
            i += 1
            while i < len(steps) and steps[i].technique == "Naked Single":
                group.append(steps[i])
                i += 1
            formatted.append(combine_step_group("Naked Singles", group))
            continue

        if style == "batched":
            group = [current]
            i += 1
            while i < len(steps) and steps[i].technique == current.technique:
                group.append(steps[i])
                i += 1
            technique = current.technique if len(group) == 1 else plural_technique_name(current.technique)
            formatted.append(combine_step_group(technique, group))
            continue

        formatted.append(current)
        i += 1

    return formatted


def group_progress_propagations(steps: Sequence[ExplanationStep]) -> List[ExplanationStep]:
    """Combine consecutive propagation steps for progress-board rendering."""
    grouped: List[ExplanationStep] = []
    i = 0
    while i < len(steps):
        current = steps[i]
        if current.technique != "Propagation":
            grouped.append(current)
            i += 1
            continue

        group = [current]
        i += 1
        while i < len(steps) and steps[i].technique == "Propagation":
            group.append(steps[i])
            i += 1

        technique = "Propagation" if len(group) == 1 else "Propagations"
        grouped.append(combine_step_group(technique, group))

    return grouped


def steps_for_progress(steps: Sequence[ExplanationStep], style: str) -> List[ExplanationStep]:
    """Return styled steps with propagation groups applied."""
    return group_progress_propagations(steps_for_style(steps, style))


def format_steps(steps: Sequence[ExplanationStep], style: str) -> List[str]:
    """Format explanation steps as printable text lines."""
    styled_steps = steps_for_style(steps, style)
    if style == "detailed":
        return [detailed_move_text(step) for step in styled_steps]
    return [compact_move_text(step) for step in styled_steps]


def ansi_text(text: str, *, fg: Optional[int] = None, bg: Optional[int] = None, bold: bool = False, enabled: bool = True) -> str:
    """Return ANSI-styled text when color output is enabled."""
    if not enabled:
        return text

    codes: list[str] = []
    if bold:
        codes.append("1")
    if fg is not None:
        codes.append(str(fg))
    if bg is not None:
        codes.append(str(bg))
    if not codes:
        return text
    return f"\033[{';'.join(codes)}m{text}\033[0m"


def styled_cell(
    segments: Sequence[Tuple[str, Optional[int], Optional[int], bool]],
    width: int,
    use_color: bool,
    *,
    bg: Optional[int] = None,
) -> str:
    visible_width = sum(len(text) for text, _, _, _ in segments)
    left = max((width - visible_width) // 2, 0)
    right = max(width - visible_width - left, 0)

    parts: list[str] = []
    if left:
        parts.append(ansi_text(" " * left, bg=bg, enabled=use_color))
    for text, fg, segment_bg, bold in segments:
        parts.append(ansi_text(text, fg=fg, bg=segment_bg if segment_bg is not None else bg, bold=bold, enabled=use_color))
    if right:
        parts.append(ansi_text(" " * right, bg=bg, enabled=use_color))
    return "".join(parts)


def candidate_cell_lines(
    mask: int,
    eliminated_digits: set[int],
    fg: int,
    bold: bool,
    cell_width: int,
    use_color: bool,
    *,
    bg: Optional[int] = None,
) -> List[str]:
    digits = set[int](digits_from_mask(mask)) | eliminated_digits
    lines: list[str] = []

    for start in (1, 4, 7):
        segments: list[tuple[str, int, Optional[int], bool]] = []
        for digit in range(start, start + 3):
            if digit != start:
                segments.append((" ", fg, bg, bold))
            if digit in digits:
                digit_fg = 31 if digit in eliminated_digits else fg
                digit_bold = True if digit in eliminated_digits else bold
                segments.append((str(digit), digit_fg, bg, digit_bold))
            else:
                segments.append((" ", fg, bg, bold))
        lines.append(styled_cell(segments, cell_width, use_color, bg=bg))

    return lines


def solved_cell_lines(
    text: str,
    fg: int,
    bold: bool,
    cell_width: int,
    use_color: bool,
    *,
    bg: Optional[int] = None,
) -> List[str]:
    blank = ansi_text(" " * cell_width, bg=bg, enabled=use_color)
    value = ansi_text(text.center(cell_width), fg=fg, bg=bg, bold=bold, enabled=use_color)
    return [blank, value, blank]


@dataclass(frozen=True)
class CellRenderStyle:
    """Foreground, background, and bold settings for one rendered cell."""

    fg: int
    bold: bool
    bg: Optional[int] = None


def base_cell_style(cell: int, given_cells: set[int], solved_cells: set[int], display_as_solved: bool) -> CellRenderStyle:
    """Return the base style for a clue, solved value, or candidate cell."""
    if not display_as_solved:
        return CellRenderStyle(fg=36, bold=False)
    if cell in given_cells:
        return CellRenderStyle(fg=37, bold=True)
    if cell in solved_cells:
        return CellRenderStyle(fg=32, bold=False)
    return CellRenderStyle(fg=36, bold=False)


def highlighted_cell_style(
    cell: int,
    base_style: CellRenderStyle,
    candidate_changed: set[int],
    selected: set[int],
    causes: set[int],
) -> CellRenderStyle:
    """Apply selected, changed, or cause-cell highlighting to a base style."""
    if cell in candidate_changed and cell in selected:
        return CellRenderStyle(fg=30, bold=True, bg=42)
    if cell in candidate_changed and cell in causes:
        return CellRenderStyle(fg=30, bold=True, bg=43)
    if cell in candidate_changed:
        return CellRenderStyle(fg=37, bold=True, bg=44)
    if cell in causes:
        return CellRenderStyle(fg=30, bold=True, bg=43)
    if cell in selected:
        return CellRenderStyle(fg=30, bold=True, bg=42)
    return base_style


def render_progress_cell(
    cell: int,
    mask: int,
    given_cells: set[int],
    solved_cells: set[int],
    selected: set[int],
    causes: set[int],
    candidate_changed: set[int],
    candidate_eliminated_digits: dict[int, set[int]],
    cell_width: int,
    use_color: bool,
) -> List[str]:
    """Render one Sudoku cell as three text lines for the progress board."""
    display_as_solved = is_single(mask) and (cell in given_cells or cell in solved_cells or cell in selected)
    base_style = base_cell_style(cell, given_cells, solved_cells, display_as_solved)
    style = highlighted_cell_style(cell, base_style, candidate_changed, selected, causes)
    eliminated_digits = candidate_eliminated_digits.get(cell, set[int]())

    if display_as_solved:
        return solved_cell_lines(
            str(single_digit(mask)),
            style.fg,
            style.bold,
            cell_width,
            use_color,
            bg=style.bg,
        )

    return candidate_cell_lines(
        mask,
        eliminated_digits,
        style.fg,
        style.bold,
        cell_width,
        use_color,
        bg=style.bg,
    )


def render_progress_grid(
    candidates: Sequence[int],
    given_cells: set[int],
    solved_cells: set[int],
    selected_cells: Iterable[int],
    candidate_eliminations: Iterable[Elimination],
    cause_cells: Iterable[int],
    use_color: bool,
) -> str:
    """Render a full 9x9 progress board with candidate mini-grids.

    The color roles match README.md: clues, solved values, selected cells,
    changed candidates, elimination sources, and eliminated candidates.
    """
    selected = set[int](selected_cells)
    candidate_eliminated_digits: dict[int, set[int]] = {}
    for elimination in candidate_eliminations:
        candidate_eliminated_digits.setdefault(elimination.cell, set[int]()).add(elimination.digit)
    candidate_changed = set[int](candidate_eliminated_digits)
    causes = set[int](cause_cells)
    lines: list[str] = []
    cell_width = 9

    for r in range(9):
        if r and r % 3 == 0:
            lines.append("-" * 101)

        row_lines: list[list[str]] = [[], [], []]
        for c in range(9):
            if c and c % 3 == 0:
                for line_parts in row_lines:
                    line_parts.append("|")

            cell = rc_to_i(r, c)
            mask = candidates[cell]
            cell_lines = render_progress_cell(
                cell,
                mask,
                given_cells,
                solved_cells,
                selected,
                causes,
                candidate_changed,
                candidate_eliminated_digits,
                cell_width,
                use_color,
            )

            for subline, rendered_cell in zip_pairs(row_lines, cell_lines):
                subline.append(rendered_cell)

        lines.extend(" ".join(row_line) for row_line in row_lines)

    return "\n".join(lines)


def wait_for_keypress(enabled: bool) -> bool:
    """Wait for interactive step navigation and return false on quit."""
    if not enabled or not sys.stdin.isatty():
        return True

    print("Press any key for next move, or q to quit...", end="", flush=True)
    try:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            key = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except KeyboardInterrupt:
        print()
        return False
    except Exception:
        try:
            key = input()
        except KeyboardInterrupt:
            print()
            return False
    print()
    return key.lower() != "q" and key != "\x03"


def print_progress_steps(
    steps: Sequence[ExplanationStep],
    given_cells: set[int],
    initial_candidates: Sequence[int],
    style: str,
    use_color: bool,
    pause_after_move: bool,
) -> None:
    """Print interactive progress boards for explanation steps."""
    print("Legend:")
    print(
        "  "
        + ansi_text("original clue", fg=37, bold=True, enabled=use_color)
        + "  "
        + ansi_text("solved value", fg=32, enabled=use_color)
        + "  "
        + ansi_text("candidates", fg=36, enabled=use_color)
        + "  "
        + ansi_text("selected this step", fg=30, bg=42, bold=True, enabled=use_color)
        + "  "
        + ansi_text("candidates changed", fg=37, bg=44, bold=True, enabled=use_color)
        + "  "
        + ansi_text("elimination source", fg=30, bg=43, bold=True, enabled=use_color)
        + "  "
        + ansi_text("eliminated candidate", fg=31, bold=True, enabled=use_color)
    )
    print()

    print("Before step 1: candidates")
    solved_cells = set[int](given_cells)
    print(render_progress_grid(initial_candidates, given_cells, solved_cells, [], [], [], use_color))
    print()

    for i, step in enumerate[ExplanationStep](steps_for_progress(steps, style), start=1):
        print(f"{i:02d}. {step.summary()} [{timing_text(step)}]")
        details = move_change_details(step)
        if details:
            print(f"    Changes: {', '.join(details)}")
        if step.after_candidates is None:
            print("No board snapshot available for this step.")
        else:
            selected_cells = {placement.cell for placement in step.placements}
            solved_cells.update(placement.cell for placement in step.placements)
            print(
                render_progress_grid(
                    step.after_candidates,
                    given_cells,
                    solved_cells,
                    selected_cells,
                    step.eliminations,
                    [cell for cell in step.cause_cells if cell not in selected_cells],
                    use_color,
                )
            )
        print()
        if not wait_for_keypress(pause_after_move):
            print("Step-by-step display stopped.")
            return


def print_timing_summary(timing_stats: dict[str, TechniqueTiming]) -> None:
    """Print aggregate timing statistics for techniques that were used."""
    if not timing_stats:
        return

    rows = [
        (technique, stats)
        for technique, stats in timing_stats.items()
        if stats.used
    ]
    if not rows:
        return

    rows.sort(key=lambda item: (-item[1].used, item[0]))
    print()
    print("Technique timing summary:")
    print("Technique                 Used  Runs  Success  Total ms  Avg ms")
    print("------------------------  ----  ----  -------  --------  ------")
    for technique, stats in rows:
        print(
            f"{technique[:24]:24}  "
            f"{stats.used:4d}  "
            f"{stats.attempts:4d}  "
            f"{stats.success_percent:6.1f}%  "
            f"{stats.total_ms:8.2f}  "
            f"{stats.average_ms:6.2f}"
        )
