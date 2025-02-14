*** Settings ***
Documentation    Untitled
Library    Lib.CommonLibrary
Library    Lib.HMILibrary


*** Variables ***
${TIMEOUT}    30s

*** Test Cases ***
HMI基本功能測試
    [Tags]    required
    [Documentation]    測試HMI的基本交互功能
    ...    
    ...    Preconditions:
    ...    - 確保HMI系統已啟動
    ...    - 檢查所有顯示元件正常
    click_button    button_id=${home_button}    delay=${0.5}
    input_text    field_id=${search_input}    text=${測試文字}    clear_first=${True}
    verify_display_value    display_id=${status_display}    expected_value=${就緒}    timeout=${5}
    select_from_dropdown    dropdown_id=${mode_selector}    option=${高級模式}
    check_element_state    element_id=${advanced_settings_button}    state=${enabled}
