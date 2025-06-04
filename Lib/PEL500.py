import serial
import serial.tools.list_ports
import time

class PEL500:
    """Control class for PEL-500 Series Electronic Load"""

    def __init__(self, port=None, baudrate=115200):
        """Initialize the electronic load connection

        Args:
            port (str): COM port (e.g. 'COM1'). If None, will prompt for selection
            baudrate (int): Baud rate, default 115200
        """

        print(f"Connecting to {port}...")

        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1
        )

    def __del__(self):
        """Close serial connection when object is deleted"""
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()

    def send_command(self, cmd):
        """Send command to the device and get response

        Args:
            cmd (str): Command to send

        Returns:
            str: Device response if any
        """
        if not cmd.endswith('\n'):
            cmd += '\n'
        self.ser.write(cmd.encode())
        time.sleep(0.1)  # Give device time to process

        if '?' in cmd:  # If it's a query command
            return self.ser.readline().decode().strip()

    def set_mode(self, mode):
        """Set the operation mode

        Args:
            mode (str): 'CC', 'CR', 'CV' or 'CP'
        """
        self.send_command(f"MODE {mode}")

    def set_current(self, current, level="HIGH"):
        """Set current in CC mode

        Args:
            current (float): Current value in Amps
            level (str): "HIGH" or "LOW"
        """
        self.send_command(f"CURR:{level} {current}")

    def set_resistance(self, resistance, level="HIGH"):
        """Set resistance in CR mode

        Args:
            resistance (float): Resistance value in Ohms
            level (str): "HIGH" or "LOW"
        """
        self.send_command(f"RES:{level} {resistance}")

    def set_voltage(self, voltage, level="HIGH"):
        """Set voltage in CV mode

        Args:
            voltage (float): Voltage value in Volts
            level (str): "HIGH" or "LOW"
        """
        self.send_command(f"VOLT:{level} {voltage}")

    def set_power(self, power, level="HIGH"):
        """Set power in CP mode

        Args:
            power (float): Power value in Watts
            level (str): "HIGH" or "LOW"
        """
        self.send_command(f"CP:{level} {power}")

    def load_on(self):
        """Turn on the load"""
        self.send_command("LOAD ON")

    def load_off(self):
        """Turn off the load"""
        self.send_command("LOAD OFF")

    def measure_voltage(self):
        """Measure current voltage

        Returns:
            float: Measured voltage in Volts
        """
        try:
            return float(self.send_command("MEAS:VOLT?"))
        except:
            return None

    def measure_current(self):
        """Measure current Current

        Returns:
            float: Measured current in Amps
        """
        try:
            return float(self.send_command("MEAS:CURR?"))
        except:
            return None

    def measure_power(self):
        """Measure current power

        Returns:
            float: Measured power in Watts
        """
        try:
            return float(self.send_command("MEAS:POW?"))
        except:
            return None


    def set_dynamic_parameters(self, t_high, t_low, rise_rate, fall_rate):
        """Set dynamic mode parameters

        Args:
            t_high (float): High level time in ms
            t_low (float): Low level time in ms
            rise_rate (float): Current rise rate in A/μs
            fall_rate (float): Current fall rate in A/μs
        """
        self.send_command(f"PERD:HIGH {t_high}")
        self.send_command(f"PERD:LOW {t_low}")
        self.send_command(f"RISE {rise_rate}")
        self.send_command(f"FALL {fall_rate}")

    def close(self):
        """Safely close the serial connection"""
        try:
            if hasattr(self, 'ser'):
                if self.ser.is_open:
                    # Turn off load before closing
                    try:
                        self.load_off()
                    except:
                        pass  # Ignore errors during load_off

                    # Close the serial connection
                    self.ser.close()
                    print(f"COM port {self.ser.port} closed successfully")
        except Exception as e:
            print(f"Error while closing COM port: {str(e)}")
