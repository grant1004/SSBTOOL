*** Settings ***
Documentation    Untitled
Library    Lib.CommonLibrary


*** Variables ***
${TIMEOUT}    30s

*** Test Cases ***
Execute Keyword - send_can_message [id]1954952952128
    [Tags]    auto-generated    optional
    [Documentation]    發送 CAN 訊息
    send_can_message    can_id=500    payload=50    node=1    can_type=0
