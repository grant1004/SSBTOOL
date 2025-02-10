*** Settings ***
Documentation     Simple test suite for testing Robot Framework listener API
Library           BuiltIn
Library           DateTime

*** Variables ***
${MIN_DELAY}      1
${MAX_DELAY}      10

*** Test Cases ***
Test Various Delays
    Long Process With Database
    Complex Calculation Process
    Network Communication Simulation
    File Processing Operation
    Heavy Resource Task

*** Keywords ***
Long Process With Database
    ${delay}=    Evaluate    random.randint(${MIN_DELAY}, ${MAX_DELAY})    random
    Log    Starting database operation simulation...
    Sleep    ${delay}
    Log    Database operation completed after ${delay} seconds

Complex Calculation Process
    ${delay}=    Evaluate    random.randint(${MIN_DELAY}, ${MAX_DELAY})    random
    Log    Starting complex calculation...
    Sleep    ${delay}
    Log    Calculation completed after ${delay} seconds

Network Communication Simulation
    ${delay}=    Evaluate    random.randint(${MIN_DELAY}, ${MAX_DELAY})    random
    Log    Initiating network communication...
    Sleep    ${delay}
    Log    Network communication completed after ${delay} seconds

File Processing Operation
    ${delay}=    Evaluate    random.randint(${MIN_DELAY}, ${MAX_DELAY})    random
    Log    Starting file processing...
    Sleep    ${delay}
    Log    File processing completed after ${delay} seconds

Heavy Resource Task
    ${delay}=    Evaluate    random.randint(${MIN_DELAY}, ${MAX_DELAY})    random
    Log    Starting resource-intensive task...
    Sleep    ${delay}
    Log    Resource-intensive task completed after ${delay} seconds