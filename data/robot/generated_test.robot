*** Settings ***
Documentation    Untitled
Library    Lib.CommonLibrary


*** Variables ***
${TIMEOUT}    30s

*** Test Cases ***
Execute Keyword - delay [id]2363243361920
    [Tags]    auto-generated    optional
    [Documentation]    暫停執行指定的秒數 參數: seconds: 暫停的秒數，可以是整數或浮點數 reason: 可選參數，記錄暫停原因
    delay    seconds=3    reason=None

Execute Keyword - send_can_message [id]2363243236928
    [Tags]    auto-generated    optional
    [Documentation]    發送 CAN 訊息
    send_can_message    can_id=400    payload=50    node=1    can_type=0

Execute Keyword - delay [id]2363231715520
    [Tags]    auto-generated    optional
    [Documentation]    暫停執行指定的秒數 參數: seconds: 暫停的秒數，可以是整數或浮點數 reason: 可選參數，記錄暫停原因
    delay    seconds=4    reason=None
