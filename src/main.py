import sys
from PySide6.QtWidgets import QApplication
import asyncio
from ui.main_window import MainWindow
from qasync import QEventLoop, QApplication
from app_coordinator import ApplicationFactory


def main():
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # 創建主視窗
    coordinator = ApplicationFactory.create_production_app()
    # 初始化應用程式
    if not coordinator.initialize():
        sys.exit(1)

    coordinator.start()

    try:
        # 使用 loop.run_forever() 代替直接調用
        with loop:
            loop.run_forever()
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        print("Closing application...")

        # 運行事件循環
        result = app.exec()

        # 清理
        coordinator.shutdown()

        # 確保事件迴圈正確關閉
        if not loop.is_closed():
            loop.close()


        return result


if __name__ == '__main__':
    sys.exit(main())