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
    source_digit_roles = {
        cell_digit: role
        for move in moves
        for cell_digit, role in move.source_digit_roles.items()
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
    combined_move.source_digit_roles = source_digit_roles
    combined_move.timing_ms = sum(move.timing_ms for move in moves)
    after_candidates = moves[-1].after_candidates[:] if moves[-1].after_candidates is not None else None
    return ExplanationStep(combined_move, after_candidates, sorted(changed_cells))


def combine_propagation_with_selection(selection: ExplanationStep, propagation: ExplanationStep) -> ExplanationStep:
    """Attach a propagation step to the placement step that caused it."""
    combined_move = Move(
        technique=selection.technique,
        difficulty=max(selection.difficulty, propagation.difficulty),
        reason=selection.reason,
        placements=selection.placements[:],
        eliminations=selection.eliminations[:] + propagation.eliminations[:],
    )
    combined_move.cause_cells = sorted(set[int](selection.cause_cells) | set[int](propagation.cause_cells))
    combined_move.source_digit_roles = {
        **selection.source_digit_roles,
        **propagation.source_digit_roles,
    }
    combined_move.timing_ms = selection.timing_ms + propagation.timing_ms
    changed_cells = sorted(set[int](selection.changed_cells) | set[int](propagation.changed_cells))
    after_candidates = propagation.after_candidates[:] if propagation.after_candidates is not None else None
    return ExplanationStep(combined_move, after_candidates, changed_cells)


def combine_propagation_steps(steps: Sequence[ExplanationStep]) -> List[ExplanationStep]:
    """Merge propagation into the placement step whose selected cell caused it."""
    combined: List[ExplanationStep] = []
    for step in steps:
        if step.technique != "Propagation" or not combined:
            combined.append(step)
            continue

        previous = combined[-1]
        placed_cells = {placement.cell for placement in previous.placements}
        if placed_cells and any(cause_cell in placed_cells for cause_cell in step.cause_cells):
            combined[-1] = combine_propagation_with_selection(previous, step)
        else:
            combined.append(step)
    return combined


def steps_for_style(steps: Sequence[ExplanationStep], style: str) -> List[ExplanationStep]:
    """Return steps transformed according to a CLI step style."""
    steps = combine_propagation_steps(steps)
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


@dataclass(frozen=True)
class RenderStyle:
    """Foreground, background, and bold settings for rendered text."""

    fg: Optional[int] = None
    bg: Optional[int] = None
    bold: bool = False


ANSI_FG_BLACK = 30
ANSI_FG_RED = 31
ANSI_FG_GREEN = 32
ANSI_FG_YELLOW = 33
ANSI_FG_BLUE = 34
ANSI_FG_MAGENTA = 35
ANSI_FG_CYAN = 36
ANSI_FG_WHITE = 37

ANSI_FG_BRIGHT_BLACK = 90
ANSI_FG_BRIGHT_RED = 91
ANSI_FG_BRIGHT_GREEN = 92
ANSI_FG_BRIGHT_YELLOW = 93
ANSI_FG_BRIGHT_BLUE = 94
ANSI_FG_BRIGHT_MAGENTA = 95
ANSI_FG_BRIGHT_CYAN = 96
ANSI_FG_BRIGHT_WHITE = 97

ANSI_BG_BLACK = 40
ANSI_BG_RED = 41
ANSI_BG_GREEN = 42
ANSI_BG_YELLOW = 43
ANSI_BG_BLUE = 44
ANSI_BG_MAGENTA = 45
ANSI_BG_CYAN = 46
ANSI_BG_WHITE = 47

ANSI_BG_BRIGHT_BLACK = 100
ANSI_BG_BRIGHT_RED = 101
ANSI_BG_BRIGHT_GREEN = 102
ANSI_BG_BRIGHT_YELLOW = 103
ANSI_BG_BRIGHT_BLUE = 104
ANSI_BG_BRIGHT_MAGENTA = 105
ANSI_BG_BRIGHT_CYAN = 106
ANSI_BG_BRIGHT_WHITE = 107

STYLE_GIVEN = RenderStyle(fg=ANSI_FG_WHITE, bold=True)
STYLE_SOLVED = RenderStyle(fg=ANSI_FG_GREEN)
STYLE_CANDIDATE = RenderStyle(fg=ANSI_FG_CYAN)
STYLE_SELECTED = RenderStyle(fg=ANSI_FG_BLACK, bg=ANSI_BG_GREEN, bold=True)
STYLE_CHANGED = RenderStyle(fg=ANSI_FG_WHITE, bg=ANSI_BG_BLUE, bold=True)
STYLE_SELECTED_CHANGED = RenderStyle(fg=ANSI_FG_BLACK, bg=ANSI_BG_GREEN, bold=True)
STYLE_DECISION_SOURCE = RenderStyle(fg=ANSI_FG_BLACK, bg=ANSI_BG_YELLOW, bold=True)
STYLE_REMOVED_CANDIDATE = RenderStyle(fg=ANSI_FG_RED, bold=True)
STYLE_MAIN_SOURCE_DIGIT = RenderStyle(fg=ANSI_FG_BLUE, bold=True)
STYLE_SHARED_SOURCE_DIGIT = RenderStyle(fg=ANSI_FG_BRIGHT_BLUE, bold=True)


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
    source_digit_roles: dict[int, str],
    fg: Optional[int],
    bold: bool,
    cell_width: int,
    use_color: bool,
    *,
    bg: Optional[int] = None,
) -> List[str]:
    digits = set[int](digits_from_mask(mask)) | eliminated_digits
    lines: list[str] = []

    for start in (1, 4, 7):
        segments: list[tuple[str, Optional[int], Optional[int], bool]] = []
        for digit in range(start, start + 3):
            if digit != start:
                segments.append((" ", fg, bg, bold))
            if digit in digits:
                if digit in eliminated_digits:
                    digit_style = STYLE_REMOVED_CANDIDATE
                elif digit in source_digit_roles:
                    digit_style = source_digit_style(source_digit_roles[digit])
                else:
                    digit_style = RenderStyle(fg=fg, bg=bg, bold=bold)
                segments.append((
                    str(digit),
                    digit_style.fg,
                    digit_style.bg if digit_style.bg is not None else bg,
                    digit_style.bold,
                ))
            else:
                segments.append((" ", fg, bg, bold))
        lines.append(styled_cell(segments, cell_width, use_color, bg=bg))

    return lines


def solved_cell_lines(
    text: str,
    fg: Optional[int],
    bold: bool,
    cell_width: int,
    use_color: bool,
    *,
    bg: Optional[int] = None,
    source_digit_roles: dict[int, str] | None = None,
) -> List[str]:
    if source_digit_roles and text.isdigit() and int(text) in source_digit_roles:
        source_style = source_digit_style(source_digit_roles[int(text)])
        fg = source_style.fg
        bold = source_style.bold
    blank = ansi_text(" " * cell_width, bg=bg, enabled=use_color)
    value = ansi_text(text.center(cell_width), fg=fg, bg=bg, bold=bold, enabled=use_color)
    return [blank, value, blank]


def source_digit_style(role: str) -> RenderStyle:
    """Return the style for a decision-source digit role."""
    if role == "secondary":
        return STYLE_SHARED_SOURCE_DIGIT
    return STYLE_MAIN_SOURCE_DIGIT


def base_cell_style(cell: int, given_cells: set[int], solved_cells: set[int], display_as_solved: bool) -> RenderStyle:
    """Return the base style for a clue, solved value, or candidate cell."""
    if not display_as_solved:
        return STYLE_CANDIDATE
    if cell in given_cells:
        return STYLE_GIVEN
    if cell in solved_cells:
        return STYLE_SOLVED
    return STYLE_CANDIDATE


def highlighted_cell_style(
    cell: int,
    base_style: RenderStyle,
    candidate_changed: set[int],
    selected: set[int],
    causes: set[int],
) -> RenderStyle:
    """Apply selected, changed, or cause-cell highlighting to a base style."""
    if cell in candidate_changed and cell in selected:
        return STYLE_SELECTED_CHANGED
    if cell in causes:
        return STYLE_DECISION_SOURCE
    if cell in candidate_changed:
        return STYLE_CHANGED
    if cell in selected:
        return STYLE_SELECTED
    return base_style


def render_progress_cell(
    cell: int,
    mask: int,
    given_cells: set[int],
    solved_cells: set[int],
    selected: set[int],
    causes: set[int],
    source_digit_roles_by_cell: dict[int, dict[int, str]],
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
    source_digit_roles = source_digit_roles_by_cell.get(cell, {})

    if display_as_solved:
        return solved_cell_lines(
            str(single_digit(mask)),
            style.fg,
            style.bold,
            cell_width,
            use_color,
            bg=style.bg,
            source_digit_roles=source_digit_roles,
        )

    return candidate_cell_lines(
        mask,
        eliminated_digits,
        source_digit_roles,
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
    source_digit_roles: dict[tuple[int, int], str] | None = None,
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
    if source_digit_roles is None:
        decision_digits = {digit for digits in candidate_eliminated_digits.values() for digit in digits}
        source_digit_roles = {
            (cell, digit): "primary"
            for cell in causes
            for digit in decision_digits
        }
    source_digit_roles_by_cell: dict[int, dict[int, str]] = {}
    for (cell, digit), role in source_digit_roles.items():
        source_digit_roles_by_cell.setdefault(cell, {})[digit] = role
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
                source_digit_roles_by_cell,
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
        + ansi_text("original clue", fg=STYLE_GIVEN.fg, bold=STYLE_GIVEN.bold, enabled=use_color)
        + "  "
        + ansi_text("solved value", fg=STYLE_SOLVED.fg, bold=STYLE_SOLVED.bold, enabled=use_color)
        + "  "
        + ansi_text("candidates", fg=STYLE_CANDIDATE.fg, bold=STYLE_CANDIDATE.bold, enabled=use_color)
        + "  "
        + ansi_text(
            "selected this step",
            fg=STYLE_SELECTED.fg,
            bg=STYLE_SELECTED.bg,
            bold=STYLE_SELECTED.bold,
            enabled=use_color,
        )
        + "  "
        + ansi_text(
            "candidates changed",
            fg=STYLE_CHANGED.fg,
            bg=STYLE_CHANGED.bg,
            bold=STYLE_CHANGED.bold,
            enabled=use_color,
        )
        + "  "
        + ansi_text(
            "decision source",
            fg=STYLE_DECISION_SOURCE.fg,
            bg=STYLE_DECISION_SOURCE.bg,
            bold=STYLE_DECISION_SOURCE.bold,
            enabled=use_color,
        )
        + "  "
        + ansi_text(
            "main source digit",
            fg=STYLE_MAIN_SOURCE_DIGIT.fg,
            bg=STYLE_DECISION_SOURCE.bg,
            bold=STYLE_MAIN_SOURCE_DIGIT.bold,
            enabled=use_color,
        )
        + "  "
        + ansi_text(
            "shared source digit",
            fg=STYLE_SHARED_SOURCE_DIGIT.fg,
            bg=STYLE_DECISION_SOURCE.bg,
            bold=STYLE_SHARED_SOURCE_DIGIT.bold,
            enabled=use_color,
        )
        + "  "
        + ansi_text(
            "eliminated candidate",
            fg=STYLE_REMOVED_CANDIDATE.fg,
            bold=STYLE_REMOVED_CANDIDATE.bold,
            enabled=use_color,
        )
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
                    step.source_digit_roles or None,
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
        if stats.used and technique != "Propagation"
    ]
    if not rows:
        return

    rows.sort(key=lambda item: (-item[1].used, item[0]))
    print()
    print("Technique timing summary:")
    print("Technique                 Used  Runs    Found  Total ms  Avg ms")
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
