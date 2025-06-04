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

    # ⭐ 新增：設置全局訪問點，讓 Robot Framework Library 能夠訪問
    import __main__
    __main__.app_coordinator = coordinator

    # 也可以設置更直接的訪問方式
    __main__.device_business_model = coordinator.get_service("device_business_model")

    coordinator.start()

    try:
        # 使用 loop.run_forever() 代替直接調用
        with loop:
            loop.run_forever()

    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        print("Closing application...")

        # 清理
        coordinator.shutdown()

        # 清理全局變量
        if hasattr(__main__, 'app_coordinator'):
            delattr(__main__, 'app_coordinator')
        if hasattr(__main__, 'device_business_model'):
            delattr(__main__, 'device_business_model')

        # 確保事件迴圈正確關閉
        if not loop.is_closed():
            loop.close()

        return 0



if __name__ == '__main__':
    sys.exit(main())