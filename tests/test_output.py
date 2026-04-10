"""Tests for output.py: OutputBuilder size budgeting."""

import pytest

from llm_commit_helper.output import OutputBuilder, format_file_header


def test_output_builder_within_budget() -> None:
    builder = OutputBuilder(max_total_size=1000)
    assert builder.add_section("hello\n") is True
    assert builder.is_truncated is False


def test_output_builder_exceeds_budget() -> None:
    builder = OutputBuilder(max_total_size=10)
    assert builder.add_section("short\n") is True
    assert builder.add_section("this is way too long\n") is False
    assert builder.is_truncated is True


def test_output_builder_tracks_truncated_files() -> None:
    builder = OutputBuilder(max_total_size=10)
    builder.add_section("x\n")
    builder.add_section("y" * 50 + "\n", file_path="big_file.py")
    output = builder.build(header="header\n", footer_template="\nfooter {total_chars}\n")
    assert "big_file.py" in output
    assert "OUTPUT TRUNCATED" in output


def test_output_builder_full_output_no_truncation() -> None:
    builder = OutputBuilder(max_total_size=10000)
    builder.add_section("section1\n")
    builder.add_section("section2\n")
    output = builder.build(header="=== Header ===\n", footer_template="\n=== End ({total_chars}) ===\n")
    assert "section1" in output
    assert "section2" in output
    assert "OUTPUT TRUNCATED" not in output
    assert "End (" in output


@pytest.mark.parametrize(
    ("path", "label", "extra", "expected"),
    [
        ("foo.py", "modified", "", "--- File: foo.py [modified] ---"),
        ("bar.v", "excluded", "", "--- File: bar.v [excluded] ---"),
        ("baz.py", "modified", "formatting-only", "--- File: baz.py [modified] [formatting-only] ---"),
    ],
)
def test_format_file_header(path: str, label: str, extra: str, expected: str) -> None:
    result = format_file_header(path, label, extra)
    assert expected in result


# Local Variables:
# eval: (blacken-mode)
# End:
