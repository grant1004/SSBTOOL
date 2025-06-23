import asyncio
from typing import Dict, List, Optional, Any, Set
from PySide6.QtCore import QObject, Signal, QTimer, Qt
import os
import shutil
import webbrowser
import glob
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import QFileDialog, QMessageBox

from src.business_models.execution_business_model import TestExecutionBusinessModel
# 導入接口
from src.interfaces.execution_interface import (
    IExecutionController, ITestExecutionBusinessModel, ITestCompositionModel, IReportGenerationModel,
    TestItem, ExecutionResult, ExecutionConfiguration, TestItemType, IExecutionView, ICompositionView,
    IControlView, ExecutionState
)

# 導入 MVC 基類
from src.mvc_framework.base_controller import BaseController
from src.mvc_framework.event_bus import event_bus
from src.ui.components import ExportDialog


class ExecutionController(BaseController, IExecutionController):

    def __init__(self, execution_business_model: TestExecutionBusinessModel):
        super().__init__()
        # 註冊業務模型
        self._run_case_views = None
        self._composition_views = None
        self._control_views = None
        self.execution_business_model = None

        self.register_model("execution_business_model", execution_business_model)



    #region BaseController
    def register_model(self, name: str, model: QObject):
        super().register_model(name, model)
        self.execution_business_model = model
        # 連接模型的通用信號
        if hasattr(model, 'execution_state_changed'):
            model.execution_state_changed.connect(self._on_state_changed)

    def register_view(self, view) -> None:
        """註冊測試案例視圖"""
        registered_as = []

        # 檢查並註冊執行視圖介面
        if isinstance(view, IExecutionView):
            self._run_case_views = view
            if view not in self._device_views:
                self._device_views.append(view)
                registered_as.append("IExecutionView")

        # 檢查並註冊組合視圖介面
        if isinstance(view, ICompositionView):
            self._composition_views = view
            if view not in self._device_views:
                self._device_views.append(view)
                registered_as.append("ICompositionView")

        # 檢查並註冊控制視圖介面
        if isinstance(view, IControlView):
            self._control_views = view
            if view not in self._device_views:
                self._device_views.append(view)
                registered_as.append("IControlView")

        view.user_action.connect(self.handle_user_action)
        self.execution_business_model.test_progress.connect(
            self._run_case_views.update_progress, Qt.ConnectionType.QueuedConnection
        )
        if registered_as:
            interfaces_str = ", ".join(registered_as)
            self._logger.info(f"Registered {type(view).__name__} as: {interfaces_str}")
        else:
            self._logger.warning(f"No recognized interfaces found for {type(view).__name__}")

    def _get_action_handler_map(self) -> Dict[str, callable]:
        """
        🔑 關鍵：將用戶操作映射到 IExecutionController 接口方法
        """
        return {
            # 執行相關操作 -> IExecutionController 方法
            "start_execution": self.handle_run_request,
            "stop_execution": self.handle_stop_request,

            # 組合相關操作 -> IExecutionController 方法
            "add_test_item": self.handle_test_item_added,
            "remove_test_item": self.handle_test_item_removed,
            "move_test_item": self.handle_test_item_moved,
            "clear_test_composition": self.handle_test_item_clear,

            # 文件操作 -> IExecutionController 方法
            "generate_test_file": self.handle_generate_request,
            "import_test_composition": self.handle_import_request,
            "generate_execution_report": self.handle_report_request,
        }


    #endregion

    #region 組合相關操作

    def handle_test_item_added(self, action_data: Dict[str, Any], item_type: TestItemType) -> None:
        """
        處理測試項目添加 - 支援位置插入

        action_data 結構：
        {
            "item_data": {
                "test_item": TestItem,
                "test_data": Dict
            },
            "item_type": TestItemType,
            "insert_index": Optional[int]  # 新增：插入位置
        }
        """
        try:
            item_data = action_data.get('item_data', {})
            test_item = item_data.get('test_item')
            insert_index = action_data.get('insert_index')  # 新增

            if not test_item:
                self._logger.error("No test_item found in action_data")
                return

            # 1. 添加到業務模型（先添加到末尾）
            success = self.execution_business_model.add_test_item(test_item)

            if not success:
                self._logger.error(f"Failed to add test item: {test_item.id}")
                return

            # 2. 如果指定了位置且不是末尾，則移動到指定位置
            if insert_index is not None:
                current_order = self.execution_business_model.get_item_order()
                current_position = len(current_order) - 1  # 剛添加的項目在末尾

                # 只有當指定位置不同於當前位置時才移動
                if insert_index != current_position:
                    move_success = self.execution_business_model.move_test_item(
                        test_item.id, insert_index
                    )
                    if move_success:
                        self._logger.info(f"Moved item {test_item.id} to position {insert_index}")

            # 3. 通知視圖更新 UI
            if self._composition_views:
                self._composition_views.add_test_item_ui(test_item, insert_index)

            # 4. 更新控制狀態
            if self._control_views:
                self._control_views.update_control_state(ExecutionState.IDLE)

            self._logger.info(f"Test item added: {test_item.id} at position {insert_index}")

        except Exception as e:
            self._logger.error(f"Error in handle_test_item_added: {e}")

    def handle_test_item_removed(self, item_id: str) -> None:
        success = self.execution_business_model.remove_test_item(item_id)

        if success:
            # 3. 通知 View 更新 UI（如果需要)
            if self._composition_views:
                self._composition_views.remove_test_item_ui(item_id)

            self._logger.info(f"Test item remove: {item_id}")

        else:
            self._logger.error(f"Failed to remove test item: {item_id}")

    def handle_test_item_moved(self, item_id: str, direction: str) -> None:
        """
        處理測試項目移動請求

        協調流程：
        1. 獲取當前順序
        2. 計算新位置
        3. 更新 Model
        4. 通知 View 更新顯示
        """
        try:
            # 1. 從 Model 獲取當前項目順序
            current_order = self.execution_business_model.get_item_order()

            if item_id not in current_order:
                self._logger.error(f"Item {item_id} not found in current order")
                return

            # 2. 計算新位置
            current_index = current_order.index(item_id)
            new_index = self._calculate_new_position(current_index, direction, len(current_order))

            if new_index == current_index:
                self._logger.info("Item already at boundary, cannot move")
                return

            # 3. 在 Model 中更新位置
            success = self.execution_business_model.move_test_item(item_id, new_index)

            if success:
                # 4. 獲取更新後的順序
                new_order = self.execution_business_model.get_item_order()

                # 5. 通知所有 View 更新顯示
                if self._composition_views:
                    self._composition_views.update_test_item_order(new_order)

                self._logger.info(f"Moved item {item_id} from {current_index} to {new_index}")
            else:
                self._logger.error(f"Failed to move item {item_id}")

        except Exception as e:
            self._logger.error(f"Error handling item move: {e}")

    def _calculate_new_position(self, current_index: int, direction: str, total_items: int) -> int:
        """計算移動後的新位置"""
        if direction == "up" and current_index > 0:
            return current_index - 1
        elif direction == "down" and current_index < total_items - 1:
            return current_index + 1
        else:
            return current_index  # 不能移動

    def handle_test_item_clear(self) -> None:
        """
        處理清空所有測試項目的請求

        注意：修正了接口定義，清空操作不需要 item_id 和 direction 參數

        協調流程：
        1. 檢查當前狀態（是否正在執行）
        2. 獲取當前項目列表（用於日誌或撤銷）
        3. 清空 Model 中的數據
        4. 通知所有 View 更新
        5. 記錄操作歷史
        """
        try:
            # 1. 檢查執行狀態
            current_state = self.get_current_execution_status()
            if current_state == ExecutionState.RUNNING:
                self._logger.warning("Cannot clear items while execution is running")
                return

            # 2. 獲取當前項目（用於記錄）
            current_items = self.execution_business_model.get_test_items()
            items_count = len(current_items)

            if items_count == 0:
                self._logger.info("No items to clear")
                return

            # 3. 記錄將要清空的項目（可用於撤銷功能）
            cleared_items_data = self._create_items_snapshot(current_items)

            # 4. 在 Model 中清空數據
            self.execution_business_model.clear_test_items()

            # 5. 通知所有 View 更新
            if self._composition_views:
                self._composition_views.clear_all_test_items_ui()

            if self._run_case_views:
                self._run_case_views.reset_execution_display()

            # 7. 記錄操作歷史（可用於撤銷）
            self._record_operation_history({
                "operation": "clear_all",
                "items_count": items_count,
                "cleared_items": cleared_items_data,
                "timestamp": self._get_timestamp_qt()
            })

            # 8. 顯示操作結果
            self.operation_completed.emit("clear_test_composition", True)

            self._logger.info(f"Cleared {items_count} test items")

        except Exception as e:
            self._logger.error(f"Error clearing test items: {e}")
            self.operation_completed.emit("clear_test_composition", False)
            # self._handle_error("clear_items_failed", str(e))

    def _record_operation_history(self, operation_data: Dict[str, Any]):
        """記錄操作歷史"""
        # 實現操作歷史記錄，可用於撤銷功能
        if not hasattr(self, '_operation_history'):
            self._operation_history = []

        self._operation_history.append(operation_data)

        # 限制歷史記錄數量
        if len(self._operation_history) > 50:
            self._operation_history.pop(0)

    def _create_items_snapshot(self, items: List[TestItem]) -> List[Dict[str, Any]]:
        """創建項目快照（用於撤銷或歷史記錄）"""
        return [
            {
                "id": item.id,
                "type": item.type.value,
                "name": item.name,
                "config": item.config.copy(),
                "status": item.status.value
            }
            for item in items
        ]

    def _get_timestamp_qt(self) -> str:
        """使用 Qt 格式的時間戳"""
        from PySide6.QtCore import QDateTime
        return QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss.zzz")

    def handle_undo_clear(self) -> None:
        """撤銷清空操作 """
        if not hasattr(self, '_operation_history') or not self._operation_history:
            return

        last_operation = self._operation_history[-1]
        if last_operation.get("operation") == "clear_all":
            cleared_items = last_operation.get("cleared_items", [])

            # 恢復項目
            for item_data in cleared_items:
                self.handle_test_item_added(item_data, TestItemType(item_data["type"]))

            self._operation_history.pop()
            self._logger.info("Undo clear operation completed")

    # endregion

    # region execution request

    async def handle_run_request(self) -> None:
        exe_config = self.execution_business_model.generate_execution_config("Untitled")
        await self.execution_business_model.start_execution(exe_config)

    async def handle_stop_request(self) -> None:
        print("Received stop request")
        await self.execution_business_model.stop_execution()

    async def handle_generate_request(self, export_config: Dict[str, Any]):
        """顯示 Export 對話框並處理 generate command"""
        # 導入對話框（延遲導入避免循環依賴）

        # 獲取主視窗和主題管理器
        main_window = self._get_main_window()
        theme_manager = getattr(main_window, 'theme_manager', None) if main_window else None

        # 顯示對話框
        export_data = ExportDialog.show_export_dialog(theme_manager, main_window)

        if export_data:
            # 用戶確認了，執行 generate command
            name_text = export_data['name']
            category = export_data['category']
            priority = export_data['priority']
            description = export_data['description']

            print(f"Exporting test case: {name_text}")
            print(f"Category: {category}, Priority: {priority}")
            print(f"Description: {export_data['description']}")

            return self.execution_business_model.generate_testcase(name_text, category, priority, description)
        else:
            # 用戶取消了
            print("Export cancelled by user")
            return None

    async def handle_import_request(self) -> None:
        print("Received handle_import_request")
        # file_path = self._show_choose_file_dialog()
        # await self.execution_business_model.import_testcase(file_path)

    async def handle_report_request(self) -> None:
        """處理報告請求 - 先選擇資料夾，再複製到資料夾內"""
        try:
            # 1. 找到最新的報告文件
            latest_report = self._find_latest_report()
            if not latest_report:
                return

            # 2. 顯示資料夾選擇對話框（而不是檔案保存對話框）
            target_folder = self._show_folder_selection_dialog()
            if not target_folder:
                # 用戶取消了選擇
                return

            # 3. 複製報告文件到資料夾（target_folder 是資料夾路徑）
            success = self._copy_report_files(latest_report, target_folder)
            if not success:
                return

            # 4. 在瀏覽器中打開保存的報告
            report_file = os.path.join(target_folder, "report.html")
            self._open_report_in_browser(report_file)

        except Exception as e:
            self._logger.error(f"Error in handle_report_request: {e}")
            self._show_error_message("處理報告失敗", f"無法處理測試報告：{str(e)}")

    def _show_folder_selection_dialog(self) -> str:
        """顯示另存新檔對話框，創建 TestReport_時間戳 資料夾"""
        try:
            # 獲取主視窗作為父視窗
            main_window = self._get_main_window()

            # 生成帶時間戳的資料夾名稱
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_folder_name = f"TestReport_{timestamp}"

            # 獲取用戶桌面路徑作為預設目錄
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.exists(desktop_path):
                desktop_path = os.path.expanduser("~")

            default_path = os.path.join(desktop_path, default_folder_name)

            # 顯示另存新檔對話框
            folder_path, _ = QFileDialog.getSaveFileName(
                parent=main_window,
                caption="建立測試報告資料夾",
                dir=default_path,
                filter="資料夾 (*)"
            )

            if folder_path:
                self._logger.info(f"Will create report folder: {folder_path}")
                return folder_path
            else:
                self._logger.info("User cancelled folder creation")
                return None

        except Exception as e:
            self._logger.error(f"Error in folder selection dialog: {e}")
            self._show_error_message("資料夾選擇錯誤", f"無法顯示資料夾選擇對話框：{str(e)}")
            return None

    def _find_latest_report(self) -> str:
        """找到最新的報告文件"""
        try:
            # 獲取報告目錄
            project_root = self._get_project_root()
            report_dir = os.path.join(project_root, "src", "report")

            if not os.path.exists(report_dir):
                self._show_error_message("報告目錄不存在", "尚未執行任何測試，請先運行測試案例。")
                return None

            # 搜索報告文件
            patterns = [
                os.path.join(report_dir, "report.html"),
                os.path.join(report_dir, "**/report.html"),
                os.path.join(report_dir, "**/*report*.html")
            ]

            report_files = []
            for pattern in patterns:
                report_files.extend(glob.glob(pattern, recursive=True))

            if not report_files:
                self._show_error_message("找不到報告文件", "沒有找到任何測試報告，請先運行測試案例。")
                return None

            # 返回最新的報告文件
            latest_report = max(report_files, key=os.path.getmtime)
            self._logger.info(f"Found latest report: {latest_report}")
            return latest_report

        except Exception as e:
            self._logger.error(f"Error finding latest report: {e}")
            self._show_error_message("查找報告失敗", f"無法找到測試報告：{str(e)}")
            return None

    def _show_save_report_dialog(self, source_report_path: str) -> str:
        """顯示另存新檔對話框"""
        try:
            # 獲取主視窗作為父視窗
            main_window = self._get_main_window()

            # 生成預設檔名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"TestReport_{timestamp}.html"

            # 獲取用戶桌面路徑作為預設目錄
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.exists(desktop_path):
                desktop_path = os.path.expanduser("~")  # 備用：使用用戶主目錄

            default_path = os.path.join(desktop_path, default_filename)

            # 顯示另存新檔對話框
            file_path, selected_filter = QFileDialog.getSaveFileName(
                parent=main_window,
                caption="儲存測試報告",
                dir=default_path,
                filter="HTML 文件 (*.html);;所有文件 (*.*)"
            )

            if file_path:
                # 確保檔案有 .html 副檔名
                if not file_path.lower().endswith('.html'):
                    file_path += '.html'

                self._logger.info(f"User selected save path: {file_path}")
                return file_path
            else:
                self._logger.info("User cancelled save dialog")
                return None

        except Exception as e:
            self._logger.error(f"Error in save dialog: {e}")
            self._show_error_message("保存對話框錯誤", f"無法顯示保存對話框：{str(e)}")
            return None

    def _copy_report_files(self, source_report_path: str, target_report_path: str) -> bool:
        """複製報告文件及相關資源到新位置"""
        try:
            # 獲取源文件目錄
            source_dir = os.path.dirname(source_report_path)

            # 將目標路徑視為資料夾路徑，而不是文件路徑
            target_dir = target_report_path  # 這裡是資料夾路徑

            # 確保目標目錄存在
            os.makedirs(target_dir, exist_ok=True)

            # 1. 複製主要的 report.html 文件到目標資料夾
            target_report_file = os.path.join(target_dir, "report.html")
            shutil.copy2(source_report_path, target_report_file)
            self._logger.info(f"Copied main report: {source_report_path} -> {target_report_file}")

            # 2. 查找並複製相關的資源文件
            related_files = self._find_related_report_files(source_dir)

            for related_file in related_files:
                try:
                    relative_path = os.path.relpath(related_file, source_dir)
                    target_file_path = os.path.join(target_dir, relative_path)

                    # 確保目標子目錄存在
                    target_file_dir = os.path.dirname(target_file_path)
                    if target_file_dir:
                        os.makedirs(target_file_dir, exist_ok=True)

                    # 複製文件
                    shutil.copy2(related_file, target_file_path)
                    self._logger.debug(f"Copied related file: {relative_path}")

                except Exception as e:
                    self._logger.warning(f"Failed to copy related file {related_file}: {e}")
                    # 繼續複製其他文件，不中斷整個過程

            # 3. 顯示成功消息
            copied_count = len(related_files) + 1  # +1 for main report
            self._show_info_message(
                "報告保存成功",
                f"已成功保存測試報告到資料夾：\n{target_dir}\n\n共複製 {copied_count} 個文件"
            )

            return True

        except Exception as e:
            self._logger.error(f"Error copying report files: {e}")
            self._show_error_message("保存報告失敗", f"無法保存測試報告：{str(e)}")
            return False

    def _find_related_report_files(self, report_dir: str) -> list:
        """查找與報告相關的資源文件"""
        related_files = []

        try:
            # Robot Framework 常見的相關文件
            related_patterns = [
                "log.html",  # 詳細日誌
                "output.xml",  # 原始輸出
                "*.png",  # 截圖
                "*.jpg", "*.jpeg",  # 圖片
                "*.css",  # 樣式文件
                "*.js",  # JavaScript 文件
                "robot-*.html",  # 其他 robot 生成的文件
            ]

            for pattern in related_patterns:
                pattern_path = os.path.join(report_dir, pattern)
                matching_files = glob.glob(pattern_path)
                related_files.extend(matching_files)

            # 遞歸查找子目錄中的資源
            for root, dirs, files in os.walk(report_dir):
                # 跳過太深的目錄層級
                if root.count(os.sep) - report_dir.count(os.sep) > 2:
                    continue

                for file in files:
                    file_path = os.path.join(root, file)
                    # 只包含特定類型的文件
                    if any(file.lower().endswith(ext) for ext in ['.css', '.js', '.png', '.jpg', '.jpeg']):
                        if file_path not in related_files:
                            related_files.append(file_path)

            self._logger.info(f"Found {len(related_files)} related files")
            return related_files

        except Exception as e:
            self._logger.error(f"Error finding related files: {e}")
            return []

    def _open_report_in_browser(self, report_path: str) -> None:
        """在瀏覽器中打開報告"""
        try:
            # 轉換為絕對路徑並創建 file:// URL
            abs_path = os.path.abspath(report_path)
            file_url = Path(abs_path).as_uri()

            # 在瀏覽器中打開
            webbrowser.open(file_url)

            self._show_info_message(
                "報告已開啟",
                f"測試報告已在瀏覽器中開啟：\n{os.path.basename(report_path)}"
            )

            self._logger.info(f"Opened report in browser: {report_path}")

        except Exception as e:
            self._logger.error(f"Failed to open report in browser: {e}")

            # 備用方案：使用系統默認程式打開
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(report_path)
                elif os.name == 'posix':  # macOS/Linux
                    os.system(
                        f'open "{report_path}"' if os.uname().sysname == 'Darwin' else f'xdg-open "{report_path}"')

                self._show_info_message("報告已開啟", "測試報告已使用系統默認程式開啟")

            except Exception as e2:
                self._logger.error(f"Backup method also failed: {e2}")
                self._show_error_message(
                    "開啟報告失敗",
                    f"無法開啟測試報告。\n報告已保存到：{report_path}\n請手動開啟該文件。"
                )

    def _on_state_changed(self, old_state: ExecutionState, new_state: ExecutionState):
        self.notify_views(
            "execution_state_changed",
            old_state=old_state,
            new_state=new_state
        )
    # endregion

    # region  ==================== 輔助方法 ====================

    def _get_project_root(self) -> str:
        """獲取項目根目錄"""
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def _get_main_window(self):
        """獲取主視窗"""
        if not self._run_case_views:
            return None

        parent = self._run_case_views.parent()
        while parent:
            if hasattr(parent, 'theme_manager'):
                return parent
            parent = parent.parent()
        return None

    def _show_info_message(self, title: str, message: str):
        """顯示信息消息"""
        try:
            main_window = self._get_main_window()
            QMessageBox.information(main_window, title, message)
        except Exception as e:
            self._logger.error(f"Error showing info message: {e}")
            print(f"INFO: {title} - {message}")

    def _show_error_message(self, title: str, message: str):
        """顯示錯誤消息"""
        try:
            main_window = self._get_main_window()
            QMessageBox.critical(main_window, title, message)
        except Exception as e:
            self._logger.error(f"Error showing error message: {e}")
            print(f"ERROR: {title} - {message}")

    # endregion

    def get_current_execution_status(self) -> ExecutionState:
        pass
        # return self._run_case_views.get_current_execution_state()


