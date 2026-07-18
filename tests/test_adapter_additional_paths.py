from unittest.mock import MagicMock, patch

from PIL import Image
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.escpos_printer.const import CONF_PRINTER_NAME, DOMAIN


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


async def test_print_image_resizes_large_local_image(hass, tmp_path, caplog):  # type: ignore[no-untyped-def]
    await _setup_entry(hass)

    # Create a big image to trigger resize (>512px width)
    img_path = tmp_path / "big.png"
    img = Image.new("L", (1024, 200))
    img.save(img_path)

    fake = MagicMock()
    with patch("escpos.printer.Dummy", return_value=fake):
        await hass.services.async_call(
            DOMAIN,
            "print_image",
            {"image": str(img_path), "high_density": True},
            blocking=True,
        )
    # Ensure image() was called and resize log present
    assert fake.image.called
    assert any("Resized image" in rec.message for rec in caplog.records)


async def test_beep_success_branch(hass, caplog):  # type: ignore[no-untyped-def]
    await _setup_entry(hass)
    fake = MagicMock()
    # Provide buzzer attribute to go through success path
    fake.buzzer = MagicMock()
    with patch("escpos.printer.Dummy", return_value=fake):
        await hass.services.async_call(DOMAIN, "beep", {"times": 2, "duration": 3}, blocking=True)
    fake.buzzer.assert_called()
    assert any("beep begin" in rec.message for rec in caplog.records)


async def test_configured_timeout_reaches_ipp(hass):  # type: ignore[no-untyped-def]
    """The config entry timeout must be passed to pyipp as request_timeout."""
    import sys

    from custom_components.escpos_printer.const import CONF_TIMEOUT

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TimeoutPrinter",
        data={CONF_PRINTER_NAME: "TimeoutPrinter", CONF_TIMEOUT: 7.4},
        unique_id="cups_TimeoutPrinter",
    )
    entry.add_to_hass(hass)
    with patch("escpos.printer.Dummy"):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    fake_ipp_class = sys.modules["pyipp"].IPP
    fake_ipp_class.last_request_timeout = None

    await hass.services.async_call(DOMAIN, "feed", {"lines": 1}, blocking=True)

    # 7.4 rounds to pyipp's integer request_timeout of 7
    assert fake_ipp_class.last_request_timeout == 7


async def test_failed_op_does_not_mark_success(hass):  # type: ignore[no-untyped-def]
    """A failing job must raise and must not flip the Online status to on."""
    from homeassistant.exceptions import HomeAssistantError
    import pytest

    entry = await _setup_entry(hass)
    adapter = hass.data[DOMAIN][entry.entry_id]["adapter"]

    fake = MagicMock()
    fake.cut.side_effect = RuntimeError("cutter jammed")
    with patch("escpos.printer.Dummy", return_value=fake):
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(DOMAIN, "cut", {"mode": "full"}, blocking=True)

    assert adapter.get_status() is not True


async def test_successful_qr_marks_success_and_notifies(hass):  # type: ignore[no-untyped-def]
    """Any successful job (not just print_text) marks the printer reachable."""
    entry = await _setup_entry(hass)
    adapter = hass.data[DOMAIN][entry.entry_id]["adapter"]

    seen: list[bool] = []
    adapter.add_status_listener(seen.append)

    await hass.services.async_call(DOMAIN, "print_qr", {"data": "hello"}, blocking=True)

    assert adapter.get_status() is True
    assert seen
    assert seen[-1] is True
