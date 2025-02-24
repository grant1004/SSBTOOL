*** Settings ***
Documentation    Untitled
Library    Lib.BatteryLibrary


*** Variables ***
${TIMEOUT}    30s

*** Test Cases ***
Execute Keyword - send_can_message [id]2820524682368
    [Tags]    auto-generated    optional
    [Documentation]    發送 CAN 訊息
    send_can_message    can_id=401    payload=11    node=1    can_type=0

Execute Keyword - send_can_message [id]2820510780288
    [Tags]    auto-generated    optional
    [Documentation]    發送 CAN 訊息
    send_can_message    can_id=402    payload=22    node=1    can_type=0

Execute Keyword - send_can_message [id]2820524575232
    [Tags]    auto-generated    optional
    [Documentation]    發送 CAN 訊息
    send_can_message    can_id=403    payload=33    node=1    can_type=0

Execute Keyword - send_can_message [id]2820524483072
    [Tags]    auto-generated    optional
    [Documentation]    發送 CAN 訊息
    send_can_message    can_id=404    payload=44    node=1    can_type=0
