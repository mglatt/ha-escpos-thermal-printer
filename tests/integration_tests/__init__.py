"""Reusable ESC/POS output parsing and validation toolkit.

This package used to host a full integration-test framework that drove the
integration against a direct-TCP ESC/POS printer emulator. That transport no
longer matches the integration, which submits jobs to CUPS over IPP, so the
socket server, resilience/performance suites, and the Home Assistant socket
harness were removed.

What remains is the transport-independent, reusable core:

- ``emulator`` - an ESC/POS byte-stream parser and a parsed-command state model.
- ``fixtures`` - helpers to generate ESC/POS test content and to assert on the
  parsed output.

These are intended as building blocks for a future CUPS/IPP-based test suite
that validates the ESC/POS bytes the integration generates.
"""

from .emulator import Command, EscposCommandParser, PrinterState, PrintJob
from .fixtures import MockDataGenerator, VerificationUtilities

__all__ = [
    'Command',
    'EscposCommandParser',
    'MockDataGenerator',
    'PrintJob',
    'PrinterState',
    'VerificationUtilities',
]
