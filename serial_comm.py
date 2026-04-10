# ═══════════════════════════════════════════════════════════════
#  SERIAL COMMUNICATION - Serial port handling
# ═══════════════════════════════════════════════════════════════

import serial.tools.list_ports


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


class SerialConnection:
    """Handle serial communication with LDC1101."""

    def __init__(self, port=None, baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.connected = False

    def connect(self):
        """Establish serial connection."""
        if self.port is None:
            return False

        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            self.connected = True
            return True
        except serial.SerialException:
            self.connected = False
            return False

    def disconnect(self):
        """Close serial connection."""
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.connected = False

    def write_register(self, address, value):
        """Write value to register address.

        SPI framing: send address byte, then send value byte.
        """
        if not self.connected:
            return False

        try:
            # LDC1101 write: send address first, then value
            self.serial.write(bytes([address]))
            self.serial.write(bytes([value]))
            return True
        except serial.SerialException:
            return False

    def read_register(self, address):
        """Read value from register address.

        SPI framing: send (0x80 | address), then read response byte.
        """
        if not self.connected:
            return None

        try:
            # LDC1101 read: send 0x80 | address to indicate read operation
            cmd = bytes([0x80 | address])
            self.serial.write(cmd)
            response = self.serial.read(1)
            if response:
                return response[0]
            return None
        except serial.SerialException:
            return None