"""Reusable ESC/POS byte-stream parsing pieces for integration testing.

This package retains the transport-independent parts of the former virtual
printer emulator: the ESC/POS command parser and the parsed-command/print-job
state model. They can be reused to validate the ESC/POS byte stream the
integration generates before it is submitted to CUPS over IPP.

The direct-TCP socket server, connection/resilience error simulator, and the
Home Assistant socket harness that used to live here were removed when the
integration moved to a CUPS-only architecture.
"""

from .command_parser import EscposCommandParser
from .printer_state import Command, PrinterState, PrintJob

__all__ = [
    'Command',
    'EscposCommandParser',
    'PrintJob',
    'PrinterState',
]
