"""Tests for newline / text-wrapping behaviour in print_text."""

import sys
from unittest.mock import call, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.escpos_printer.const import CONF_PRINTER_NAME, DOMAIN
from custom_components.escpos_printer.printer import EscposPrinterAdapter, PrinterConfig


# ---------------------------------------------------------------------------
# Unit tests for _wrap_text (pure, no HA needed)
# ---------------------------------------------------------------------------


def _make_adapter(line_width: int = 48) -> EscposPrinterAdapter:
    cfg = PrinterConfig(
        printer_name="TestPrinter",
        line_width=line_width,
        codepage=None,
        cups_server=None,
    )
    return EscposPrinterAdapter(cfg)


class TestWrapText:
    """Unit tests for EscposPrinterAdapter._wrap_text."""

    def test_no_wrap_when_line_width_zero(self) -> None:
        adapter = _make_adapter(line_width=0)
        text = "Hello world " * 10
        assert adapter._wrap_text(text) == text

    def test_simple_wrap(self) -> None:
        adapter = _make_adapter(line_width=10)
        result = adapter._wrap_text("Hello World")
        # drop_whitespace=False preserves trailing space on the first wrapped line
        assert result == "Hello \nWorld"

    def test_trailing_newline_preserved(self) -> None:
        adapter = _make_adapter(line_width=48)
        text = "Hello\n"
        assert adapter._wrap_text(text).endswith("\n")

    def test_leading_newline_preserved(self) -> None:
        adapter = _make_adapter(line_width=48)
        text = "\nHello"
        assert adapter._wrap_text(text).startswith("\n")

    def test_multiple_trailing_newlines_preserved(self) -> None:
        adapter = _make_adapter(line_width=48)
        text = "Hello\n\n"
        result = adapter._wrap_text(text)
        assert result.endswith("\n\n")

    def test_width_mult_1_uses_full_cols(self) -> None:
        """width_mult=1 wraps at full line_width."""
        adapter = _make_adapter(line_width=10)
        # 10-char text fits in 10 cols at normal size → no wrap
        assert adapter._wrap_text("1234567890", width_mult=1) == "1234567890"

    def test_width_mult_2_halves_effective_cols(self) -> None:
        """width_mult=2 should wrap at line_width//2 effective columns."""
        adapter = _make_adapter(line_width=10)
        # 6-char text fits at normal but overflows at double-width (effective=5)
        result = adapter._wrap_text("123456", width_mult=2)
        assert "\n" in result, f"Expected wrap but got: {result!r}"

    def test_width_mult_3_thirds_effective_cols(self) -> None:
        """width_mult=3 should wrap at line_width//3 effective columns."""
        adapter = _make_adapter(line_width=12)
        # 5-char text fits at normal (12 cols) but overflows at triple-width (effective=4)
        result = adapter._wrap_text("Hello", width_mult=3)
        assert "\n" in result, f"Expected wrap but got: {result!r}"

    def test_wrap_with_leading_trailing_newlines_and_width_mult(self) -> None:
        """_wrap_text with width_mult preserves surrounding newlines."""
        adapter = _make_adapter(line_width=10)
        text = "\n>>> LIZ <<<\n"
        # ">>> LIZ <<<" is 12 chars; effective width at mult=2 is 5, so wraps
        result = adapter._wrap_text(text, width_mult=2)
        assert result.startswith("\n")
        assert result.endswith("\n")

    def test_short_double_width_text_no_wrap(self) -> None:
        """Short double-width text that fits should not be wrapped."""
        adapter = _make_adapter(line_width=48)
        # ">>> LIZ <<<" = 12 chars; at double-width effective=24; 12 < 24 → no wrap
        text = "\n>>> LIZ <<<\n"
        result = adapter._wrap_text(text, width_mult=2)
        lines = [ln for ln in result.split("\n") if ln]
        assert len(lines) == 1, f"Expected no wrap for short text: {result!r}"


# ---------------------------------------------------------------------------
# Integration tests: extra LF bytes appended for height > 1
# ---------------------------------------------------------------------------


async def _setup_entry(hass):  # type: ignore[no-untyped-def]
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TestPrinter",
        data={CONF_PRINTER_NAME: "TestPrinter"},
        unique_id="cups_TestPrinter",
    )
    entry.add_to_hass(hass)
    with patch("escpos.printer.Dummy"):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_double_height_trailing_newline_appends_extra_crlf(hass):  # type: ignore[no-untyped-def]
    """Double-height text ending with \\n should have one extra CR+LF appended."""
    await _setup_entry(hass)

    dummy_cls = sys.modules["escpos.printer"].Dummy
    raw_calls: list[bytes] = []

    original_raw = dummy_cls._raw

    def spy_raw(self, data: bytes, *args, **kwargs):  # type: ignore[no-untyped-def]
        raw_calls.append(data)
        return original_raw(self, data, *args, **kwargs)

    with patch.object(dummy_cls, "_raw", spy_raw):
        await hass.services.async_call(
            DOMAIN,
            "print_text",
            {"text": "BIG\n", "height": "double"},
            blocking=True,
        )

    # ESC @ must be the first _raw call (print-position reset)
    assert raw_calls and raw_calls[0] == bytes([0x1B, 0x40]), (
        f"Expected ESC @ as first _raw call, got: {raw_calls}"
    )
    # Exactly one extra CR+LF (b"\r\n") should be appended via _raw
    assert b"\r\n" in raw_calls, (
        f"Expected extra CR+LF in _raw calls for double-height text, got: {raw_calls}"
    )
    assert raw_calls.count(b"\r\n") == 1, (
        f"Expected exactly one extra CR+LF for hmult=2 (got {raw_calls.count(b'\\r\\n')}): {raw_calls}"
    )
    # No ESC 3 / ESC 2 should be emitted (those commands were removed)
    assert not any(b"\x1b\x33" in rc for rc in raw_calls), (
        "ESC 3 must not be sent — use extra CR+LF instead"
    )
    assert not any(rc == bytes([0x1B, 0x32]) for rc in raw_calls), (
        "ESC 2 must not be sent — use extra CR+LF instead"
    )


async def test_normal_height_no_extra_crlf(hass):  # type: ignore[no-untyped-def]
    """Normal-height text must not receive any extra CR+LF bytes."""
    await _setup_entry(hass)

    dummy_cls = sys.modules["escpos.printer"].Dummy
    raw_calls: list[bytes] = []

    original_raw = dummy_cls._raw

    def spy_raw(self, data: bytes, *args, **kwargs):  # type: ignore[no-untyped-def]
        raw_calls.append(data)
        return original_raw(self, data, *args, **kwargs)

    with patch.object(dummy_cls, "_raw", spy_raw):
        await hass.services.async_call(
            DOMAIN,
            "print_text",
            {"text": "Normal\n"},
            blocking=True,
        )

    # ESC @ must be the first _raw call (print-position reset)
    assert raw_calls and raw_calls[0] == bytes([0x1B, 0x40]), (
        f"Expected ESC @ as first _raw call, got: {raw_calls}"
    )
    # No extra CR+LF should be injected for hmult=1
    assert b"\r\n" not in raw_calls, (
        f"Extra CR+LF should NOT be added for normal-height text, got _raw calls: {raw_calls}"
    )
    assert not any(b"\x1b\x33" in rc for rc in raw_calls), (
        "ESC 3 n should NOT be sent for normal-height text"
    )
    assert not any(rc == bytes([0x1B, 0x32]) for rc in raw_calls), (
        "ESC 2 should NOT be sent for normal-height text"
    )


async def test_triple_height_trailing_newline_appends_two_extra_crlfs(hass):  # type: ignore[no-untyped-def]
    """Triple-height text ending with \\n should have two extra CR+LFs appended."""
    await _setup_entry(hass)

    dummy_cls = sys.modules["escpos.printer"].Dummy
    raw_calls: list[bytes] = []

    original_raw = dummy_cls._raw

    def spy_raw(self, data: bytes, *args, **kwargs):  # type: ignore[no-untyped-def]
        raw_calls.append(data)
        return original_raw(self, data, *args, **kwargs)

    with patch.object(dummy_cls, "_raw", spy_raw):
        await hass.services.async_call(
            DOMAIN,
            "print_text",
            {"text": "HUGE\n", "height": "triple"},
            blocking=True,
        )

    # ESC @ must be the first _raw call (print-position reset)
    assert raw_calls and raw_calls[0] == bytes([0x1B, 0x40]), (
        f"Expected ESC @ as first _raw call, got: {raw_calls}"
    )
    # Two extra CR+LF sequences appended in a single _raw(b"\r\n\r\n") call
    assert b"\r\n\r\n" in raw_calls, (
        f"Expected extra b'\\r\\n\\r\\n' in _raw calls for triple-height text, got: {raw_calls}"
    )
    assert not any(b"\x1b\x33" in rc for rc in raw_calls), (
        "ESC 3 must not be sent for triple-height text"
    )
