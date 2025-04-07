from abc import ABC, abstractmethod
import asyncio
from typing import Optional, Callable, Dict, Any
import threading
import time
import os
from datetime import datetime
from queue import Queue
import logging


class MessageListener(threading.Thread):
    """訊息監聽器，作為獨立線程運行"""

    def __init__(self, device_id: str, receive_func: Callable,
                 log_file: str = None, buffer_size: int = 100,
                 callback: Callable = None):
        """
        初始化監聽器

        Args:
            device_id: 設備標識
            receive_func: 從設備接收數據的函數
            log_file: 記錄文件路徑，如果為None則不記錄
            buffer_size: 緩衝區大小
            callback: 收到消息時的回調函數
        """
        super().__init__()
        self.device_id = device_id
        self.receive_func = receive_func
        self.log_file = log_file
        self.buffer_size = buffer_size
        self.callback = callback
        self.daemon = True  # 設置為守護線程，主程序結束時自動結束

        self.running = False
        self.message_queue = Queue(maxsize=buffer_size)

        # 如果指定了日誌文件，確保目錄存在
        if self.log_file:
            os.makedirs(os.path.dirname(os.path.abspath(self.log_file)), exist_ok=True)

        # 設置日誌記錄
        self.logger = logging.getLogger(f"Listener-{device_id}")
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # 控制台處理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 文件處理器（如果指定了日誌文件）
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def run(self):
        """線程運行方法"""
        self.running = True
        self.logger.info(f"Starting message listener for device {self.device_id}")

        # 如果指定了日誌文件，打開它準備寫入
        log_file_handle = None
        if self.log_file:
            try:
                log_file_handle = open(self.log_file, 'a', encoding='utf-8')
                log_file_handle.write(f"\n--- Listening session started at {datetime.now()} ---\n")
                log_file_handle.flush()
            except Exception as e:
                self.logger.error(f"Failed to open log file: {e}")
                # 繼續執行，但不會寫入文件

        try:
            while self.running:
                try:
                    # 嘗試接收訊息
                    message = self.receive_func()

                    if message:
                        # 添加時間戳
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                        formatted_message = f"[{timestamp}] {message}"

                        # 添加到隊列
                        if not self.message_queue.full():
                            self.message_queue.put(formatted_message)

                        # 寫入日誌文件
                        if log_file_handle:
                            log_file_handle.write(formatted_message + "\n")
                            log_file_handle.flush()

                        # 如果有回調函數，調用它
                        if self.callback:
                            self.callback(message)

                except Exception as e:
                    self.logger.error(f"Error receiving message: {e}")

                # 短暫休眠，避免CPU佔用過高
                time.sleep(0.001)

        finally:
            # 清理資源
            if log_file_handle:
                log_file_handle.write(f"\n--- Listening session ended at {datetime.now()} ---\n")
                log_file_handle.close()

            self.logger.info(f"Stopped message listener for device {self.device_id}")

    def stop(self):
        """停止監聽"""
        self.running = False
        # 等待線程結束
        if self.is_alive():
            self.join(timeout=2.0)  # 等待最多2秒

    def get_messages(self, count: int = 10) -> list:
        """獲取最近的訊息

        Args:
            count: 要獲取的訊息數量

        Returns:
            list: 訊息列表
        """
        messages = []
        # 從隊列中獲取指定數量的訊息
        for _ in range(min(count, self.message_queue.qsize())):
            if not self.message_queue.empty():
                messages.append(self.message_queue.get())
                self.message_queue.task_done()

        return messages
