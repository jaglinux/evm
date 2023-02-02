#!/usr/bin/env python3

# EVM From Scratch
# Python template
#
# To work on EVM From Scratch in Python:
#
# - Install Python3: https://www.python.org/downloads/
# - Go to the `python` directory: `cd python`
# - Edit `evm.py` (this file!), see TODO below
# - Run `python3 evm.py` to run the tests

#Implementation inspired by https://github.com/karmacoma-eth/smol-evm
import json
import os
import sys
from dataclasses import dataclass

# Constants
UINT256MAX = (2 ** 256) -1

inputs = len(sys.argv)
# some random high number so that by default all test cases will run
testsMax = 1000
testsRun = 0
# singleBin which contains code binary to run
singleBin = None
if inputs == 2:
    arg2 = list(sys.argv)[1]
    if "test" in arg2:
        arg2List = arg2.split('=')
        if arg2List[0] == 'test':
            singleBin = arg2List[1]
    else:
        # control the test cases numbers here
        testsMax = int(arg2)

class Stack:
    def __init__(self, size = 1024):
        self.list = []
        self.maxSize = size

    # Push max 32 bytes
    def push(self, item):
        if item > UINT256MAX:
            # TODO: handle error
            return False
        self.list.append(item)

    def pop(self):
        return self.list.pop()

class Memory:
    def __init__(self):
        self.array = bytearray();

class Context:
    def __init__(self, code, pc=0):
        self.stack = Stack(1024)
        self.memory = Memory()
        self.code = code
        self.pc = pc

def opcodeStop(ctx, dummy):
    return OpcodeResponse(True, None)

def opcodePush(ctx, pushBytes):
    data = 0
    for i in range(pushBytes):
        # Big Endian
        data = (data << 8) | ctx.code[ctx.pc]
        ctx.pc +=1
    ctx.stack.push(data)
    return OpcodeResponse(False, None)

def opcodePop(ctx, dummy):
    data = ctx.stack.pop()
    return OpcodeResponse(False, data)

def opcodeAdd(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = (a+b)
    # overflow condition
    result &= UINT256MAX
    ctx.stack.push(result)
    return OpcodeResponse(False, None)

def opcodeMul(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = (a*b)
    # overflow condition
    result &= UINT256MAX
    ctx.stack.push(result)
    return OpcodeResponse(False, None)

def opcodeSub(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = (a-b)
    # overflow condition
    # 2's signed complement, equivalent to
    # i=-1 ; i.to_bytes(32, "big", signed=True)
    # b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
    result &= UINT256MAX
    ctx.stack.push(result)
    return OpcodeResponse(False, None)

def opcodeDiv(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    # Handle Divide by 0
    if b == 0:
        result = 0
    else:
        result = int(a / b)
    ctx.stack.push(result)
    return OpcodeResponse(False, None)

def opcodeMod(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    if b == 0:
        result = 0
    else:
        result = a % b
    ctx.stack.push(result)
    return OpcodeResponse(False, None)

@dataclass
class OpcodeResponse:
    stop: bool #stop will be True for stop opcode
    data: int # pop() opcode can return data popped through this variable

class OpcodeData:
    def __init__(self, opcode, name, run, pushBytes=0):
        self.opcode = opcode
        self.name = name
        # function pointer
        self.run = run
        # if push opcode, pushBytes represents number of
        # bytes to be pushed into stack.
        self.pushBytes = pushBytes

opcode = {}
opcode[0x00] = OpcodeData(0x00, "STOP", opcodeStop)
opcode[0x60] = OpcodeData(0x60, "PUSH1", opcodePush, 1)
opcode[0x61] = OpcodeData(0x61, "PUSH2", opcodePush, 2)
opcode[0x62] = OpcodeData(0x62, "PUSH3", opcodePush, 3)
opcode[0x63] = OpcodeData(0x63, "PUSH4", opcodePush, 4)
opcode[0x64] = OpcodeData(0x64, "PUSH5", opcodePush, 5)
opcode[0x65] = OpcodeData(0x65, "PUSH6", opcodePush, 6)
opcode[0x66] = OpcodeData(0x66, "PUSH7", opcodePush, 7)
opcode[0x67] = OpcodeData(0x67, "PUSH8", opcodePush, 8)
opcode[0x68] = OpcodeData(0x68, "PUSH9", opcodePush, 9)
opcode[0x69] = OpcodeData(0x69, "PUSH10", opcodePush, 10)
opcode[0x6A] = OpcodeData(0x6A, "PUSH11", opcodePush, 11)
opcode[0x6B] = OpcodeData(0x6B, "PUSH12", opcodePush, 12)
opcode[0x6C] = OpcodeData(0x6C, "PUSH13", opcodePush, 13)
opcode[0x6D] = OpcodeData(0x6D, "PUSH14", opcodePush, 14)
opcode[0x6E] = OpcodeData(0x6E, "PUSH15", opcodePush, 15)
opcode[0x6F] = OpcodeData(0x6F, "PUSH16", opcodePush, 16)
opcode[0x70] = OpcodeData(0x70, "PUSH17", opcodePush, 17)
opcode[0x71] = OpcodeData(0x71, "PUSH18", opcodePush, 18)
opcode[0x72] = OpcodeData(0x72, "PUSH19", opcodePush, 19)
opcode[0x73] = OpcodeData(0x73, "PUSH20", opcodePush, 20)
opcode[0x74] = OpcodeData(0x74, "PUSH21", opcodePush, 21)
opcode[0x75] = OpcodeData(0x75, "PUSH22", opcodePush, 22)
opcode[0x76] = OpcodeData(0x76, "PUSH23", opcodePush, 23)
opcode[0x77] = OpcodeData(0x77, "PUSH24", opcodePush, 24)
opcode[0x78] = OpcodeData(0x78, "PUSH25", opcodePush, 25)
opcode[0x79] = OpcodeData(0x79, "PUSH26", opcodePush, 26)
opcode[0x7A] = OpcodeData(0x7A, "PUSH27", opcodePush, 27)
opcode[0x7B] = OpcodeData(0x7B, "PUSH28", opcodePush, 28)
opcode[0x7C] = OpcodeData(0x7C, "PUSH29", opcodePush, 29)
opcode[0x7D] = OpcodeData(0x7D, "PUSH30", opcodePush, 30)
opcode[0x7E] = OpcodeData(0x7E, "PUSH31", opcodePush, 31)
opcode[0x7F] = OpcodeData(0x7F, "PUSH32", opcodePush, 32)
opcode[0x50] = OpcodeData(0x50, "POP", opcodePop)
opcode[0x01] = OpcodeData(0x01, "ADD", opcodeAdd)
opcode[0x02] = OpcodeData(0x02, "MUL", opcodeMul)
opcode[0x03] = OpcodeData(0x03, "SUB", opcodeSub)
opcode[0x04] = OpcodeData(0x04, "DIV", opcodeDiv)
opcode[0x06] = OpcodeData(0x06, "MOD", opcodeMod)


def prehook(opcodeObj):
    print(f'Running opcode {hex(opcodeObj.opcode)} {opcodeObj.name}')

def evm(code, outputStackLen):
    global testsRun, testsMax
    if testsRun >= testsMax:
        sys.exit()
    testsRun+=1

    success = True
    ctx = Context(code)

    while ctx.pc < len(code):
        op = code[ctx.pc]
        # pc will always increment by 1 here
        # pc can also be incremented in PUSH opcodes
        ctx.pc += 1
        opcodeObj = opcode.get(op)
        if opcodeObj:
            prehook(opcodeObj)
            opcodeReturn = opcodeObj.run(ctx, opcodeObj.pushBytes)
            if opcodeReturn.stop == True:
                break
        else:
            print("Opcode implementation not found for ", hex(op))
            # return fake success but empty stack so that test case
            # panics with proper test name and error message
            return (success, [])
        
    result=[]
    if len(ctx.stack.list):
        if outputStackLen >= 2:
        # output format is different if output stack is greater than 2
        # check evm.json for more details.
            while len(ctx.stack.list):
                result.append(ctx.stack.pop())
        else:
            tempList = [f'{i:x}' for i in ctx.stack.list]
            print('result in hex ', ''.join(tempList))
            result.append(int(''.join(tempList), 16))
    return (success, result)

def test():
    script_dirname = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_dirname, "..", "evm.json")
    with open(json_file) as f:
        data = json.load(f)
        total = len(data)

        for i, test in enumerate(data):
            # Note: as the test cases get more complex, you'll need to modify this
            # to pass down more arguments to the evm function
            code = bytes.fromhex(test['code']['bin'])
            (success, stack) = evm(code, len(test['expect']['stack']))

            expected_stack = [int(x, 16) for x in test['expect']['stack']]
            
            if stack != expected_stack or success != test['expect']['success']:
                print(f"❌ Test #{i + 1}/{total} {test['name']}")
                if stack != expected_stack:
                    print("Stack doesn't match")
                    print(" expected:", expected_stack)
                    print("   actual:", stack)
                else:
                    print("Success doesn't match")
                    print(" expected:", test['expect']['success'])
                    print("   actual:", success)
                print("")
                print("Test code:")
                print(test['code']['asm'])
                print("")
                print("Hint:", test['hint'])
                print("")
                print(f"Progress: {i}/{len(data)}")
                print("")
                break
            else:
                print(f"✓  Test #{i + 1}/{total} {test['name']}")

if __name__ == '__main__':
    if singleBin is None:
        test()
    else:
        print('Run custom single test')
        evm(bytes.fromhex(singleBin), 1)
