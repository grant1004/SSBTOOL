import usb.core
import usb.util
import sys
import traceback


def check_usb_permissions():
    """檢查當前程序的 USB 訪問權限"""
    try:
        # 嘗試列出所有設備，如果有權限問題會拋出異常
        list(usb.core.find(find_all=True))
        return True
    except Exception as e:
        print(f"權限檢查失敗: {str(e)}")
        return False


def scan_usb_devices(target_vid=0x5458, target_pid=0x1222):
    """掃描並顯示所有 USB 設備的詳細信息"""
    print("\n=== USB 設備掃描工具 ===")
    print(f"目標設備: VID=0x{target_vid:04x}, PID=0x{target_pid:04x}")
    print("\n正在掃描所有 USB 設備...")

    try:
        # 檢查 USB 權限
        if not check_usb_permissions():
            print("警告: 可能沒有足夠的 USB 訪問權限")
            print("建議: 使用管理員權限運行程序")
            return

        # 掃描所有設備
        devices = list(usb.core.find(find_all=True))

        if not devices:
            print("未找到任何 USB 設備!")
            return

        print(f"\n找到 {len(devices)} 個 USB 設備:")
        target_found = False

        for i, device in enumerate(devices, 1):
            try:
                # 獲取設備信息
                manufacturer = "Unknown"
                product = "Unknown"
                serial = "Unknown"

                try:
                    if device.iManufacturer:
                        manufacturer = usb.util.get_string(device, device.iManufacturer)
                except:
                    pass

                try:
                    if device.iProduct:
                        product = usb.util.get_string(device, device.iProduct)
                except:
                    pass

                try:
                    if device.iSerialNumber:
                        serial = usb.util.get_string(device, device.iSerialNumber)
                except:
                    pass

                print(f"\n設備 {i}:")
                print(f"  VID: 0x{device.idVendor:04x}")
                print(f"  PID: 0x{device.idProduct:04x}")
                print(f"  製造商: {manufacturer}")
                print(f"  產品: {product}")
                print(f"  序號: {serial}")

                # 檢查是否為目標設備
                if device.idVendor == target_vid and device.idProduct == target_pid:
                    target_found = True
                    print("  ** 這是目標設備 **")

                    # 嘗試打開設備
                    try:
                        device.set_configuration()
                        print("  狀態: 可以訪問")

                        # 查找端點
                        cfg = device.get_active_configuration()
                        intf = cfg[(1, 0)]

                        ep_out = usb.util.find_descriptor(
                            intf,
                            custom_match=lambda e:
                            usb.util.endpoint_direction(e.bEndpointAddress) ==
                            usb.util.ENDPOINT_OUT)

                        ep_in = usb.util.find_descriptor(
                            intf,
                            custom_match=lambda e:
                            usb.util.endpoint_direction(e.bEndpointAddress) ==
                            usb.util.ENDPOINT_IN)

                        if ep_out and ep_in:
                            print("  端點: 找到輸入和輸出端點")
                        else:
                            print("  端點: 未找到所需端點")

                    except usb.core.USBError as e:
                        print(f"  狀態: 無法訪問 ({str(e)})")
                        print("  可能原因: 驅動程序不正確或權限不足")
                    except Exception as e:
                        print(f"  狀態: 訪問出錯 ({str(e)})")

            except Exception as e:
                print(f"\n設備 {i}: 無法獲取完整信息")
                print(f"錯誤: {str(e)}")

        if not target_found:
            print("\n未找到目標設備!")
            print("建議:")
            print("1. 確認設備是否正確連接")
            print("2. 檢查 VID/PID 是否正確")
            print("3. 使用設備管理器確認設備狀態")
            print("4. 確保安裝了正確的驅動程序 (WinUSB)")

    except Exception as e:
        print("\n掃描過程出錯:")
        print(str(e))
        print("\n詳細錯誤信息:")
        traceback.print_exc()


if __name__ == "__main__":
    # 可以從命令行接收目標 VID/PID
    vid = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x5458
    pid = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x1222

    scan_usb_devices(vid, pid)