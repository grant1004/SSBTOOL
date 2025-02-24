*** Settings ***
Documentation    Untitled
Library    Lib.BatteryLibrary


*** Variables ***
${TIMEOUT}    30s

*** Test Cases ***
Execute Keyword - send_can_message [id]2698926488960
    [Tags]    auto-generated    optional
    [Documentation]    發送 CAN 訊息
    send_can_message    can_id=None    payload=None    node=1    can_type=0
