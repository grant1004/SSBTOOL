import sys
from PySide6.QtWidgets import QApplication
import asyncio
from qasync import QEventLoop, QApplication


def main():
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # 創建主視窗
    from ui import MainWindow
    window = MainWindow()
    window.show()

    try:
        # 使用 loop.run_forever() 代替直接調用
        with loop:
            loop.run_forever()
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        print("Closing application...")

        # 安全地關閉所有視窗
        app.closeAllWindows()

        # 確保事件迴圈正確關閉
        if not loop.is_closed():
            loop.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())