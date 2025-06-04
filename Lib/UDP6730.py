import serial
import serial.tools.list_ports
import time

class UDP6730:
    """Control class for UDP6730 Series DC Power Supply"""

    def __init__(self, port=None, baudrate=9600):
        """Initialize the power supply connection

        Args:
            port (str): COM port (e.g. 'COM1'). If None, will prompt for selection
            baudrate (int): Baud rate, default 9600
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

    def get_idn(self):
        """Query device identification

        Returns:
            str: Device identification
        """
        return self.send_command("*IDN?")

    def get_voltage_setting(self):
        """Measure current voltage

        Returns:
            float: Measured voltage in Volts
        """
        try:
            return float(self.send_command("VOLT?"))
        except:
            return None

    def get_current_setting(self):
        """Measure current current

        Returns:
            float: Measured current in Amps
        """
        try:
            return float(self.send_command("CURR?"))
        except:
            return None

    def measure_voltage(self):
        """Measure current voltage

        Returns:
            float: Measured voltage in Volts
        """
        try:
            return float(self.send_command("MEASure:VOLTage?"))
        except:
            return None

    def measure_current(self):
        """Measure current A

        Returns:
            float: Measured current in A
        """
        try:
            return float(self.send_command("MEASure:CURRent?"))
        except:
            return None

    def measure_power(self):
        """Measure current power

        Returns:
            float: Measured power in Watts
        """
        try:
            return float(self.send_command("MEASure:POWEr?"))
        except:
            return None

    def set_voltage(self, voltage):
        """Set output voltage

        Args:
            voltage (float): Voltage value in Volts
        """
        formatted_voltage = f"{voltage:05.2f}"
        self.send_command(f"VOLT {formatted_voltage}")

    def set_current(self, current):
        """Set output current

        Args:
            current (float): Current value in Amps
        """
        formatted_current = f"{current:05.2f}"
        self.send_command(f"CURR {formatted_current}")

    def output_on(self):
        """Turn on the power supply output"""
        self.send_command("OUTP ON")

    def output_off(self):
        """Turn off the power supply output"""
        self.send_command("OUTP OFF")

    def get_output_state(self):
        """Get the output state

        Returns:
            bool: True if output is on, False if off
        """
        response = self.send_command("OUTP?")
        return response == "ON"

    def close(self):
        """Safely close the serial connection"""
        try:
            if hasattr(self, 'ser'):
                if self.ser.is_open:
                    # Turn off output before closing
                    try:
                        self.output_off()
                    except:
                        pass  # Ignore errors during output_off

                    # Close the serial connection
                    self.ser.close()
                    print(f"COM port {self.ser.port} closed successfully")
        except Exception as e:
            print(f"Error while closing COM port: {str(e)}")


# Example usage:
if __name__ == "__main__":
    try:
        # Create power supply object - will prompt for COM port selection
        ps = UDP6730()

        # Display device information
        print("Device ID:", ps.get_idn())

        while True:
            # Read measurements
            try:
                voltage = ps.measure_voltage()
                current = ps.measure_current()

                if all((voltage is not None, current is not None)):
                    print(f"\nVoltage: {voltage:.3f}V")
                    print(f"Current: {current:.3f}A")
                else:
                    print("Measurement error")

            except Exception as e:
                print(f"Measurement error: {e}")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'ps' in locals():
            ps.close()