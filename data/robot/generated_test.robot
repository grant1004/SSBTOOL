*** Settings ***
Documentation    Untitled
Library    Lib.BatteryLibrary


*** Variables ***
${TIMEOUT}    30s

*** Test Cases ***
Execute Keyword - send_can_message
    [Tags]    auto-generated    optional
    [Documentation]    發送 CAN 訊息
    send_can_message    can_id=0x401    payload=00 64    node=0    can_type=0
