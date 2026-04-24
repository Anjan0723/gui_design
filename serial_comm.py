# ═══════════════════════════════════════════════════════════════
#  SERIAL COMMUNICATION - Serial port handling
# ═══════════════════════════════════════════════════════════════

import logging
import serial.tools.list_ports

logger = logging.getLogger("LDC1101_Serial")


def get_available_ports():
    """Get list of available COM ports."""
    return [p.device for p in serial.tools.list_ports.comports()]


def get_mock_ports():
    """Get list of mock ports for simulation."""
    return ["COM3 (Mock)", "COM4 (Mock)"]


def refresh_ports(populate_cb, conn_label):
    """
    Refresh available ports and update UI.

    Args:
        populate_cb: Callback to set combobox values
        conn_label: Connection status label widget
    """
    ports = get_available_ports()

    if not ports:
        # Use mock ports when no real ports found
        ports = get_mock_ports()
        populate_cb(ports)
        conn_label.config(text="  NOT CONNECTED  ", bg="#cc0000")
    else:
        populate_cb(ports)
        conn_label.config(text="  CONNECTED  ", bg="#107c10")

    return ports


import threading

class SerialConnection:
    """Handle serial communication with LDC1101."""

    def __init__(self, port=None, baudrate=115200, timeout=0.1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.connected = False
        self.lock = threading.Lock()

    def connect(self):
        """Establish serial connection."""
        if self.port is None:
            logger.error("Cannot connect: port is None")
            return False

        # Pre-emptive close to break any existing hangs or locks
        try:
            if self.serial and self.serial.is_open:
                self.serial.close()
        except Exception as e:
            logger.warning(f"Error closing existing serial: {e}")

        with self.lock:
            try:
                import serial # Ensure local import is available
                self.serial = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    write_timeout=0.5 # Add write timeout to prevent hangs
                )
                self.connected = True
                logger.info(f"Connected to {self.port} at {self.baudrate} baud")
                return True
            except Exception as e:
                logger.error(f"Failed to connect to {self.port}: {e}")
                self.connected = False
                return False

    def disconnect(self):
        """Close serial connection."""
        with self.lock:
            try:
                if self.serial and self.serial.is_open:
                    self.serial.close()
                    logger.info(f"Disconnected from {self.port}")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.connected = False

    def write_register(self, address, value):
        """Write value to register address.

        SPI framing: send address byte, then send value byte.
        """
        if not self.connected:
            logger.warning(f"Write attempt while not connected: addr=0x{address:02X}, val=0x{value:02X}")
            return False

        with self.lock:
            try:
                # LDC1101 write: send address first, then value
                if self.serial:
                    self.serial.write(bytes([address]))
                    self.serial.write(bytes([value]))
                logger.debug(f"Wrote 0x{value:02X} -> 0x{address:02X}")
                return True
            except serial.SerialException as e:
                logger.error(f"Serial write error: addr=0x{address:02X}, val=0x{value:02X}, error={e}")
                self.connected = False
                return False

    def read_register(self, address):
        """Read value from register address.

        SPI framing: send (0x80 | address), then read response byte.
        """
        if not self.connected:
            logger.warning(f"Read attempt while not connected: addr=0x{address:02X}")
            return None

        with self.lock:
            try:
                # LDC1101 read: send 0x80 | address to indicate read operation
                cmd = bytes([0x80 | address])
                if self.serial:
                    self.serial.write(cmd)
                    response = self.serial.read(1)
                    if response:
                        val = response[0]
                        logger.debug(f"Read 0x{val:02X} <- 0x{address:02X}")
                        return val
                logger.warning(f"No response for read: addr=0x{address:02X}")
                return 0 # Return 0 for mock/read failure instead of crashing
            except serial.SerialException as e:
                logger.error(f"Serial read error: addr=0x{address:02X}, error={e}")
                self.connected = False
                return None