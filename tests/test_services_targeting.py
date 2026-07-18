"""Tests for service target resolution and the UTF-8 text service."""

from unittest.mock import MagicMock, patch

from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.escpos_printer.const import CONF_PRINTER_NAME, DOMAIN


async def _setup_entry(hass, name="TestPrinter"):  # type: ignore[no-untyped-def]
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=name,
        data={CONF_PRINTER_NAME: name},
        unique_id=f"cups_{name}",
    )
    entry.add_to_hass(hass)
    with patch("escpos.printer.Dummy"):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_print_text_utf8_service(hass):  # type: ignore[no-untyped-def]
    await _setup_entry(hass)
    fake = MagicMock()
    with patch("escpos.printer.Dummy", return_value=fake):
        await hass.services.async_call(
            DOMAIN,
            "print_text_utf8",
            {"text": "curly “quotes” and — dashes"},
            blocking=True,
        )
    fake.text.assert_called()
    printed = fake.text.call_args[0][0]
    # Look-alike transcoding replaces characters outside the codepage
    assert "“" not in printed


async def test_service_with_device_id_target(hass):  # type: ignore[no-untyped-def]
    entry = await _setup_entry(hass)
    registry = dr.async_get(hass)
    device = registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
    )

    fake = MagicMock()
    with patch("escpos.printer.Dummy", return_value=fake):
        await hass.services.async_call(
            DOMAIN,
            "print_text",
            {"device_id": device.id, "text": "targeted"},
            blocking=True,
        )
    fake.text.assert_called()


async def test_service_with_unknown_device_id_raises(hass):  # type: ignore[no-untyped-def]
    await _setup_entry(hass)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "print_text",
            {"device_id": "no-such-device", "text": "nope"},
            blocking=True,
        )


async def test_service_without_entries_raises(hass):  # type: ignore[no-untyped-def]
    """Broadcast targeting with no loaded entries is a validation error."""
    entry = await _setup_entry(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "print_text",
            {"text": "nobody home"},
            blocking=True,
        )
