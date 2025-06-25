import serial
import serial.tools.list_ports
import time

class UDP6730:
    """Control class for UDP6730 Series DC Power Supply"""

    def __init__(self, port="COM32", baudrate=9600):
        """Initialize the power supply connection

        Args:
            port (str): COM port (e.g. 'COM1'). If None, will prompt for selection
            baudrate (int): Baud rate, default 9600
        """
        self.port = port
        print(f"Connecting to {port}...")
        try :
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1
            )
        except :
            print(f"Connecting to {port} failed!")

    def __del__(self):
        """Close serial connection when object is deleted"""
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()

    def is_serial_connected(self):
        """檢查 serial 連線是否正常

        Returns:
            bool: True 如果連線正常，False 如果連線中斷
        """
        try:
            # 檢查 serial 物件是否存在且開啟
            if not hasattr(self, 'ser') or not self.ser.is_open:
                return False

            # 檢查 COM port 是否還存在於系統中
            available_ports = [port.device for port in serial.tools.list_ports.comports()]
            if self.port not in available_ports:
                print(f"Warning: {self.port} is no longer available in system")
                return False

            # 嘗試發送簡單的查詢命令來測試通訊
            try:
                # 清空接收緩衝區
                self.ser.reset_input_buffer()

                # 發送 IDN 查詢命令
                self.ser.write(b"*IDN?\n")
                time.sleep(0.2)

                # 檢查是否有回應
                if self.ser.in_waiting > 0:
                    response = self.ser.readline().decode().strip()
                    if response:  # 有收到回應
                        return True
                else:
                    print("Warning: No response from device")
                    return False

            except (serial.SerialException, OSError) as e:
                print(f"Serial communication error: {e}")
                return False

        except Exception as e:
            print(f"Connection check error: {e}")
            return False

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