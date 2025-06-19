# src/controllers/test_case_controller.py
"""
測試案例控制器 - 協調測試案例業務邏輯和 UI 交互
職責：
1. 協調測試案例和關鍵字的載入流程
2. 管理多個 View 的狀態同步
3. 處理搜索、過濾、分類切換等用戶操作
4. 協調跨組件的測試案例狀態通信
5. 管理載入狀態和錯誤處理
6. 提供用戶友好的操作反饋
"""

import asyncio
from typing import Dict, List, Optional, Any, Set
from PySide6.QtCore import QObject, Signal, QTimer

# 導入接口
from src.interfaces.test_case_interface import (
    ITestCaseController, ITestCaseView, TestCaseCategory, TestCaseMode,
    TestCasePriority, TestCaseInfo, KeywordInfo, SearchCriteria,
    TestCaseCategoryChangedEvent, TestCaseModeChangedEvent, TestCaseSearchEvent
)

# 導入 MVC 基類
from src.mvc_framework.base_controller import BaseController
from src.mvc_framework.event_bus import event_bus

# 導入業務模型
from src.business_models.test_case_business_model import TestCaseBusinessModel


class TestCaseController(BaseController, ITestCaseController):
    """
    測試案例控制器

    特點：
    - 智能的載入狀態管理
    - 批量視圖更新優化
    - 搜索結果緩存
    - 自動錯誤恢復
    - 用戶操作歷史記錄
    """

    # 控制器級別信號
    category_changed = Signal(TestCaseCategory, TestCaseCategory)  # old, new
    mode_changed = Signal(TestCaseMode, TestCaseMode)  # old, new
    search_results_updated = Signal(str, int)  # search_text, count
    loading_state_changed = Signal(bool)  # is_loading
    selection_changed = Signal(str, str)  # item_id, item_type

    def __init__(self, test_case_model: TestCaseBusinessModel):
        super().__init__()

        # 註冊業務模型
        self.register_model("test_case_business", test_case_model)
        self.test_case_model = test_case_model

        # 視圖管理
        self._test_case_views: List[ITestCaseView] = []

        # 狀態管理
        self._current_category = TestCaseCategory.COMMON
        self._current_mode = TestCaseMode.TEST_CASES
        self._current_search_text = ""
        self._selected_item_id: Optional[str] = None
        self._selected_item_type: Optional[str] = None

        # 數據緩存（控制器級別的快速緩存）
        self._current_test_cases: List[TestCaseInfo] = []
        self._current_keywords: List[KeywordInfo] = []
        self._search_results_cache: Dict[str, List[Any]] = {}

        # 載入狀態追蹤
        self._loading_categories: Set[TestCaseCategory] = set()
        self._pending_operations: Dict[str, bool] = {}

        # 配置選項
        self._auto_load_enabled = True
        self._search_debounce_delay = 300  # 毫秒
        self._batch_update_enabled = True
        self._error_retry_enabled = True
        self._max_search_results = 100

        # 搜索防抖定時器
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._perform_debounced_search)

        # 批量更新定時器
        self._batch_update_timer = QTimer()
        self._batch_update_timer.setSingleShot(True)
        self._batch_update_timer.timeout.connect(self._perform_batch_updates)
        self._pending_view_updates: List[tuple] = []

        # 操作歷史
        self._operation_history: List[Dict[str, Any]] = []
        self._max_history_size = 50

        # 連接業務模型事件
        self._connect_business_model_signals()

        # 設置事件總線訂閱
        self._setup_event_subscriptions()

        self._logger.info("TestCaseController initialized with coordination capabilities")

    # ==================== ITestCaseController 接口實現 ====================

    def _get_action_handler_map(self) -> Dict[str, callable]:
        """
        🔑 關鍵：將用戶操作映射到 IExecutionController 接口方法
        """
        return {
            "delete_testcase": self.delete_testcase_action,
            "category_change": self.handle_category_change,
            "mode_switch": self.handle_mode_switch,
            "search_request": self.handle_search_request,
            "test_case_selection": self.handle_test_case_selection,
            "keyword_selection": self.handle_keyword_selection,
            "refresh_request": self.handle_refresh_request
        }

    def register_view(self, view: ITestCaseView) -> None:
        """註冊測試案例視圖"""
        if view not in self._test_case_views:
            self._test_case_views.append(view)
            self._sync_view_with_current_state(view)
            view.user_action.connect(self.handle_user_action)
            self._logger.info(f"Registered test case view: {type(view).__name__}")

    def unregister_view(self, view: ITestCaseView) -> None:
        """取消註冊測試案例視圖"""
        if view in self._test_case_views:
            self._test_case_views.remove(view)
            self._logger.info(f"Unregistered test case view: {type(view).__name__}")

    def handle_category_change(self, category: TestCaseCategory) -> None:
        """
        處理分類變更請求

        協調流程：
        1. 狀態驗證和前置檢查
        2. 載入狀態管理
        3. 數據載入協調
        4. 視圖狀態同步
        5. 事件發布和歷史記錄
        """
        # if category == self._current_category:
        #     return

        operation_name = f"category_change_{self._current_category.value}_to_{category.value}"

        try:
            # 記錄操作歷史
            self._add_to_history("category_change", {
                'old_category': self._current_category,
                'new_category': category,
                'timestamp': asyncio.get_event_loop().time()
            })

            # 更新載入狀態
            if category not in self._loading_categories:
                self._set_loading_state(True)

            # 清除當前搜索和選擇
            self._clear_current_selection()
            self._clear_search_state()

            # 發出狀態變更信號
            old_category = self._current_category
            self._current_category = category
            self.category_changed.emit(old_category, category)

            # 協調數據載入 - 檢查事件循環是否存在
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._coordinate_category_data_loading(category))
            except RuntimeError:
                # 如果沒有運行中的事件循環，使用 QTimer 延遲執行
                QTimer.singleShot(10, lambda: asyncio.create_task(self._coordinate_category_data_loading(category)))

            # 發布跨組件事件
            event_bus.publish("test_case_category_changed", TestCaseCategoryChangedEvent(
                old_category, category
            ))

            self._logger.info(f"Category changed: {old_category.value} -> {category.value}")

        except Exception as e:
            self._handle_operation_error(operation_name, e)

    def handle_mode_switch(self, mode: TestCaseMode) -> None:
        """處理模式切換（測試案例 vs 關鍵字）"""
        # if mode == self._current_mode:
        #     return

        operation_name = f"mode_switch_{self._current_mode.value}_to_{mode.value}"

        try:
            # 記錄操作歷史
            self._add_to_history("mode_switch", {
                'old_mode': self._current_mode,
                'new_mode': mode,
                'category': self._current_category,
                'timestamp': asyncio.get_event_loop().time()
            })

            # 清除當前搜索和選擇
            self._clear_current_selection()
            self._clear_search_state()

            # 發出狀態變更信號
            old_mode = self._current_mode
            self._current_mode = mode
            self.mode_changed.emit(old_mode, mode)

            # 協調視圖更新
            self._coordinate_mode_switch_display()

            # 發布跨組件事件
            event_bus.publish("test_case_mode_changed", TestCaseModeChangedEvent(
                old_mode, mode
            ))

            self._logger.info(f"Mode switched: {old_mode.value} -> {mode.value}")

        except Exception as e:
            self._handle_operation_error(operation_name, e)

    def handle_search_request(self, search_text: str) -> None:
        """處理搜索請求"""
        # 防抖處理
        self._current_search_text = search_text
        self._search_timer.stop()
        self._search_timer.start(self._search_debounce_delay)

    def handle_test_case_selection(self, test_case_id: str) -> None:
        """處理測試案例選擇"""
        try:
            # 驗證測試案例存在
            test_case = self.test_case_model.get_test_case_by_id(test_case_id)
            if not test_case:
                self._notify_views_batch('show_error_message', f"測試案例不存在: {test_case_id}")
                return

            # 更新選擇狀態
            old_selection = self._selected_item_id
            self._selected_item_id = test_case_id
            self._selected_item_type = "test_case"

            # 記錄操作歷史
            self._add_to_history("test_case_selection", {
                'test_case_id': test_case_id,
                'test_case_name': test_case.name,
                'category': test_case.category,
                'timestamp': asyncio.get_event_loop().time()
            })

            # 發出選擇變更信號
            self.selection_changed.emit(test_case_id, "test_case")

            # 發布跨組件事件
            event_bus.publish("test_case_selected", {
                'test_case_id': test_case_id,
                'test_case': test_case,
                'previous_selection': old_selection
            })

            self._logger.info(f"Test case selected: {test_case_id}")

        except Exception as e:
            self._logger.error(f"Error handling test case selection: {e}")
            self._notify_views_batch('show_error_message', f"選擇測試案例時發生錯誤: {str(e)}")

    def handle_keyword_selection(self, keyword_id: str) -> None:
        """處理關鍵字選擇"""
        try:
            # 驗證關鍵字存在
            keyword = self.test_case_model.get_keyword_by_id(keyword_id)
            if not keyword:
                self._notify_views_batch('show_error_message', f"關鍵字不存在: {keyword_id}")
                return

            # 更新選擇狀態
            old_selection = self._selected_item_id
            self._selected_item_id = keyword_id
            self._selected_item_type = "keyword"

            # 記錄操作歷史
            self._add_to_history("keyword_selection", {
                'keyword_id': keyword_id,
                'keyword_name': keyword.name,
                'category': keyword.category,
                'timestamp': asyncio.get_event_loop().time()
            })

            # 發出選擇變更信號
            self.selection_changed.emit(keyword_id, "keyword")

            # 發布跨組件事件
            event_bus.publish("keyword_selected", {
                'keyword_id': keyword_id,
                'keyword': keyword,
                'previous_selection': old_selection
            })

            self._logger.info(f"Keyword selected: {keyword_id}")

        except Exception as e:
            self._logger.error(f"Error handling keyword selection: {e}")
            self._notify_views_batch('show_error_message', f"選擇關鍵字時發生錯誤: {str(e)}")

    def handle_refresh_request(self) -> None:
        """處理刷新請求"""
        operation_name = "refresh_request"

        try:
            # 記錄操作歷史
            self._add_to_history("refresh", {
                'category': self._current_category,
                'mode': self._current_mode,
                'timestamp': asyncio.get_event_loop().time()
            })

            # 設置載入狀態
            self._set_loading_state(True)

            # 清除緩存
            self._clear_search_cache()

            # 執行刷新
            asyncio.create_task(self._coordinate_refresh_operation())

            self._logger.info("Refresh requested")

        except Exception as e:
            self._handle_operation_error(operation_name, e)

    def get_current_state(self) -> Dict[str, Any]:
        """獲取當前狀態（用於狀態恢復）"""
        return {
            'current_category': self._current_category,
            'current_mode': self._current_mode,
            'current_search_text': self._current_search_text,
            'selected_item_id': self._selected_item_id,
            'selected_item_type': self._selected_item_type,
            'loading_categories': list(self._loading_categories),
            'pending_operations': self._pending_operations.copy(),
            'test_cases_count': len(self._current_test_cases),
            'keywords_count': len(self._current_keywords),
            'operation_history_count': len(self._operation_history)
        }

    def delete_testcase_action(self, testcase_id):
        success = self.test_case_model.delete_testcase_by_id(testcase_id)
        if success :
            self.handle_refresh_request()
            self._logger.info(f"delete testcase {testcase_id} success")
        else :
            self._logger.info(f"delete testcase {testcase_id} failed")

    # ==================== 協調邏輯實現 ====================

    async def _coordinate_category_data_loading(self, category: TestCaseCategory) -> None:
        """協調分類數據載入"""
        try:
            self._loading_categories.add(category)

            if self._current_mode == TestCaseMode.TEST_CASES:
                # 載入測試案例
                test_cases = await self._load_test_cases_async(category)
                self._current_test_cases = test_cases
                self._notify_views_batch('display_test_cases', test_cases)
            else:
                # 載入關鍵字
                keywords = await self._load_keywords_async(category)
                self._current_keywords = keywords
                self._notify_views_batch('display_keywords', keywords)

            # 更新分類選擇顯示
            self._notify_views_batch('update_category_selection', category)

        except Exception as e:
            self._logger.error(f"Error loading category data: {e}")
            self._notify_views_batch('show_error_message', f"載入分類數據失敗: {str(e)}")

            # 嘗試錯誤恢復
            if self._error_retry_enabled:
                await self._attempt_error_recovery("category_loading", category)

        finally:
            self._loading_categories.discard(category)
            self._set_loading_state(len(self._loading_categories) > 0)

    def _coordinate_mode_switch_display(self) -> None:
        """協調模式切換的顯示"""
        try:
            # 更新視圖模式選擇
            self._notify_views_batch('update_mode_selection', self._current_mode)

            # 根據當前模式顯示對應數據
            if self._current_mode == TestCaseMode.TEST_CASES:
                # if self._current_test_cases:
                #     self._notify_views_batch('display_test_cases', self._current_test_cases)
                # else:
                #     # 需要載入測試案例
                asyncio.create_task(self._coordinate_category_data_loading(self._current_category))
            else:
                # if self._current_keywords:
                #     self._notify_views_batch('display_keywords', self._current_keywords)
                # else:
                #     # 需要載入關鍵字
                asyncio.create_task(self._coordinate_category_data_loading(self._current_category))

        except Exception as e:
            self._logger.error(f"Error coordinating mode switch display: {e}")
            self._notify_views_batch('show_error_message', f"切換顯示模式失敗: {str(e)}")

    async def _coordinate_refresh_operation(self) -> None:
        """協調刷新操作"""
        try:
            # 刷新業務模型數據
            success = await self._refresh_business_model_async()

            if success:
                # 重新載入當前分類數據
                await self._coordinate_category_data_loading(self._current_category)
                self._notify_views_batch('show_success_message', "數據刷新完成")
            else:
                self._notify_views_batch('show_error_message', "數據刷新失敗")

        except Exception as e:
            self._logger.error(f"Error during refresh operation: {e}")
            self._notify_views_batch('show_error_message', f"刷新操作失敗: {str(e)}")

        finally:
            self._set_loading_state(False)

    def _perform_debounced_search(self) -> None:
        """執行防抖搜索"""
        search_text = self._current_search_text.strip()

        try:
            # 檢查搜索緩存
            cache_key = f"{self._current_category.value}_{self._current_mode.value}_{search_text}"
            if cache_key in self._search_results_cache:
                results = self._search_results_cache[cache_key]
                self._display_search_results(results, search_text)
                return

            # 執行新搜索
            asyncio.create_task(self._perform_search_async(search_text))

        except Exception as e:
            self._logger.error(f"Error performing debounced search: {e}")
            self._notify_views_batch('show_error_message', f"搜索失敗: {str(e)}")

    async def _perform_search_async(self, search_text: str) -> None:
        """執行異步搜索"""
        try:
            criteria = SearchCriteria(
                keyword=search_text,
                category=self._current_category,
                mode=self._current_mode
            )

            if self._current_mode == TestCaseMode.TEST_CASES:
                results = await self._search_test_cases_async(criteria)
            else:
                results = await self._search_keywords_async(criteria)

            # 限制結果數量
            if len(results) > self._max_search_results:
                results = results[:self._max_search_results]
                self._notify_views_batch('show_warning_message',
                                       f"搜索結果過多，僅顯示前 {self._max_search_results} 個結果")

            # 緩存搜索結果
            cache_key = f"{self._current_category.value}_{self._current_mode.value}_{search_text}"
            self._search_results_cache[cache_key] = results

            # 顯示結果
            self._display_search_results(results, search_text)

        except Exception as e:
            self._logger.error(f"Error performing async search: {e}")
            self._notify_views_batch('show_error_message', f"搜索執行失敗: {str(e)}")

    def _display_search_results(self, results: List[Any], search_text: str) -> None:
        """顯示搜索結果"""
        try:
            if self._current_mode == TestCaseMode.TEST_CASES:
                self._notify_views_batch('display_test_cases', results)
            else:
                self._notify_views_batch('display_keywords', results)

            # 高亮搜索結果
            if search_text:
                self._notify_views_batch('highlight_search_results', search_text)
            else:
                self._notify_views_batch('clear_search_highlight')

            # 發出搜索結果更新信號
            self.search_results_updated.emit(search_text, len(results))

            # 發布搜索事件
            event_bus.publish("test_case_search_completed", TestCaseSearchEvent(
                search_text, len(results)
            ))

            self._logger.info(f"Search completed: '{search_text}' found {len(results)} results")

        except Exception as e:
            self._logger.error(f"Error displaying search results: {e}")

    # ==================== 業務模型事件處理 ====================

    def _connect_business_model_signals(self) -> None:
        """連接業務模型信號"""
        self.test_case_model.test_cases_loaded.connect(self._on_test_cases_loaded)
        self.test_case_model.keywords_loaded.connect(self._on_keywords_loaded)
        self.test_case_model.search_completed.connect(self._on_search_completed)
        self.test_case_model.category_refreshed.connect(self._on_category_refreshed)
        self.test_case_model.validation_failed.connect(self._on_validation_failed)

    def _on_test_cases_loaded(self, category: TestCaseCategory, count: int) -> None:
        """處理測試案例載入完成"""
        self._logger.info(f"Test cases loaded: {category.value} ({count} items)")

        if category == self._current_category and self._current_mode == TestCaseMode.TEST_CASES:
            # 更新當前數據
            test_cases = self.test_case_model._test_cases_cache.get(category, [])
            self._current_test_cases = test_cases

    def _on_keywords_loaded(self, category: TestCaseCategory, count: int) -> None:
        """處理關鍵字載入完成"""
        self._logger.info(f"Keywords loaded: {category.value} ({count} items)")

        if category == self._current_category and self._current_mode == TestCaseMode.KEYWORDS:
            # 更新當前數據
            keywords = self.test_case_model._keywords_cache.get(category, [])
            self._current_keywords = keywords

    def _on_search_completed(self, search_text: str, results_count: int) -> None:
        """處理搜索完成"""
        self._logger.info(f"Search completed: '{search_text}' ({results_count} results)")

    def _on_category_refreshed(self, category: TestCaseCategory) -> None:
        """處理分類刷新完成"""
        self._logger.info(f"Category refreshed: {category.value}")

        if category == self._current_category:
            # 重新載入當前顯示的數據
            asyncio.create_task(self._coordinate_category_data_loading(category))

    def _on_validation_failed(self, item_id: str, errors: List[str]) -> None:
        """處理驗證失敗"""
        error_message = f"項目 {item_id} 驗證失敗:\n" + "\n".join(errors)
        self._notify_views_batch('show_error_message', error_message)

    # ==================== 異步操作方法 ====================

    async def _load_test_cases_async(self, category: TestCaseCategory) -> List[TestCaseInfo]:
        """異步載入測試案例"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.test_case_model.load_test_cases, category
        )

    async def _load_keywords_async(self, category: TestCaseCategory) -> List[KeywordInfo]:
        """異步載入關鍵字"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.test_case_model.load_keywords, category
        )

    async def _search_test_cases_async(self, criteria: SearchCriteria) -> List[TestCaseInfo]:
        """異步搜索測試案例"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.test_case_model.search_test_cases, criteria
        )

    async def _search_keywords_async(self, criteria: SearchCriteria) -> List[KeywordInfo]:
        """異步搜索關鍵字"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.test_case_model.search_keywords, criteria
        )

    async def _refresh_business_model_async(self) -> bool:
        """異步刷新業務模型"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.test_case_model.refresh_test_cases, self._current_category
        )

    # ==================== 視圖協調方法 ====================

    def _notify_views_batch(self, method_name: str, *args, **kwargs) -> None:
        """批量通知所有視圖"""
        if self._batch_update_enabled:
            # 添加到待處理的更新隊列
            self._pending_view_updates.append((method_name, args, kwargs))
            self._batch_update_timer.stop()
            self._batch_update_timer.start(50)  # 50ms 延遲
        else:
            self._notify_views_immediate(method_name, *args, **kwargs)

    def _notify_views_immediate(self, method_name: str, *args, **kwargs) -> None:
        """立即通知所有視圖"""
        for view in self._test_case_views:
            if hasattr(view, method_name):
                try:
                    method = getattr(view, method_name)
                    method(*args, **kwargs)
                except Exception as e:
                    self._logger.error(f"View notification failed for {method_name}: {e}")

    def _perform_batch_updates(self) -> None:
        """執行批量視圖更新"""
        try:
            for method_name, args, kwargs in self._pending_view_updates:
                self._notify_views_immediate(method_name, *args, **kwargs)
        finally:
            self._pending_view_updates.clear()

    def _sync_view_with_current_state(self, view: ITestCaseView) -> None:
        """為新視圖同步當前狀態"""
        try:
            # 同步分類和模式
            view.update_category_selection(self._current_category)
            view.update_mode_selection(self._current_mode)

            # 同步數據顯示
            if self._current_mode == TestCaseMode.TEST_CASES and self._current_test_cases:
                view.display_test_cases(self._current_test_cases)
            elif self._current_mode == TestCaseMode.KEYWORDS and self._current_keywords:
                view.display_keywords(self._current_keywords)

            # 同步搜索狀態
            if self._current_search_text:
                view.highlight_search_results(self._current_search_text)

            # 同步載入狀態
            is_loading = len(self._loading_categories) > 0
            view.show_loading_state(is_loading)

        except Exception as e:
            self._logger.error(f"Error syncing view with current state: {e}")

    # ==================== 狀態管理方法 ====================

    def _set_loading_state(self, is_loading: bool) -> None:
        """設置載入狀態"""
        self.loading_state_changed.emit(is_loading)
        self._notify_views_batch('show_loading_state', is_loading)

    def _clear_current_selection(self) -> None:
        """清除當前選擇"""
        if self._selected_item_id:
            old_id = self._selected_item_id
            self._selected_item_id = None
            self._selected_item_type = None
            self.selection_changed.emit("", "")

    def _clear_search_state(self) -> None:
        """清除搜索狀態"""
        self._current_search_text = ""
        self._notify_views_batch('clear_search_highlight')

    def _clear_search_cache(self) -> None:
        """清除搜索緩存"""
        self._search_results_cache.clear()

    def _add_to_history(self, operation_type: str, data: Dict[str, Any]) -> None:
        """添加操作到歷史記錄"""
        self._operation_history.append({
            'operation_type': operation_type,
            'data': data,
            'timestamp': asyncio.get_event_loop().time()
        })

        # 限制歷史記錄大小
        if len(self._operation_history) > self._max_history_size:
            self._operation_history.pop(0)

    # ==================== 事件總線處理 ====================

    def _setup_event_subscriptions(self) -> None:
        """設置事件總線訂閱"""
        event_bus.subscribe("system_shutdown", self._on_system_shutdown)
        event_bus.subscribe("theme_changed", self._on_theme_changed)

    def _on_system_shutdown(self, data: Any) -> None:
        """處理系統關閉"""
        self._logger.info("System shutdown received, cleaning up controller")
        self._search_timer.stop()
        self._batch_update_timer.stop()

    def _on_theme_changed(self, data: Any) -> None:
        """處理主題變更"""
        # 通知視圖更新主題
        self._notify_views_batch('update_theme')

    # ==================== 錯誤處理方法 ====================

    def _handle_operation_error(self, operation_name: str, error: Exception) -> None:
        """處理操作錯誤"""
        error_message = f"{operation_name} 失敗: {str(error)}"
        self._logger.error(error_message)

        # 通知視圖顯示錯誤
        self._notify_views_batch('show_error_message', error_message)

        # 記錄錯誤到歷史
        self._add_to_history("error", {
            'operation': operation_name,
            'error': str(error),
            'timestamp': asyncio.get_event_loop().time()
        })

    async def _attempt_error_recovery(self, error_type: str, context: Any) -> None:
        """嘗試錯誤恢復"""
        self._logger.info(f"Attempting error recovery for {error_type}")

        try:
            if error_type == "category_loading":
                # 等待一段時間後重試載入
                await asyncio.sleep(2)
                await self._coordinate_category_data_loading(context)

        except Exception as e:
            self._logger.error(f"Error recovery failed for {error_type}: {e}")

    # ==================== 配置和統計方法 ====================

    def set_auto_load(self, enabled: bool) -> None:
        """設置自動載入"""
        self._auto_load_enabled = enabled

    def set_search_debounce_delay(self, delay_ms: int) -> None:
        """設置搜索防抖延遲"""
        self._search_debounce_delay = max(100, delay_ms)

    def set_batch_update(self, enabled: bool) -> None:
        """設置批量更新"""
        self._batch_update_enabled = enabled

    def set_error_retry(self, enabled: bool) -> None:
        """設置錯誤重試"""
        self._error_retry_enabled = enabled

    def set_max_search_results(self, max_results: int) -> None:
        """設置最大搜索結果數"""
        self._max_search_results = max(10, max_results)

    def get_controller_statistics(self) -> Dict[str, Any]:
        """獲取控制器統計信息"""
        return {
            'registered_views': len(self._test_case_views),
            'current_state': self.get_current_state(),
            'loading_categories': list(self._loading_categories),
            'search_cache_size': len(self._search_results_cache),
            'operation_history_size': len(self._operation_history),
            'pending_operations': len(self._pending_operations),
            'configuration': {
                'auto_load_enabled': self._auto_load_enabled,
                'search_debounce_delay': self._search_debounce_delay,
                'batch_update_enabled': self._batch_update_enabled,
                'error_retry_enabled': self._error_retry_enabled,
                'max_search_results': self._max_search_results
            }
        }

    def get_operation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """獲取操作歷史"""
        return self._operation_history[-limit:] if limit > 0 else self._operation_history.copy()
