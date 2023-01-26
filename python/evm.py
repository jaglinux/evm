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

import json
import os

class Stack:
    def __init__(self, size = 1024):
        self.list = []
        self.maxSize = size

    def push(self, item):
        self.list.append(item)

class Memory:
    def __init__(self):
        self.array = bytearray();

class Context:
    def __init__(self, code, pc=0):
        self.stack = Stack(1024)
        self.memory = Memory()
        self.code = code
        self.pc = pc

def opcodeStop(ctx):
    return

def opcodePush1(ctx):
    ctx.pc +=1
    ctx.stack.push(ctx.code[ctx.pc])

class OpcodeData:
    def __init__(self, opcode, name, run):
        self.opcode = opcode
        self.name = name
        # function pointer
        self.run = run

opcode = {}
opcode[0x00] = OpcodeData(0x00, "STOP", opcodeStop)
opcode[0x60] = OpcodeData(0x60, "PUSH1", opcodePush1)


def prehook(opcodeObj):
    print(f'Running opcode {hex(opcodeObj.opcode)} {opcodeObj.name}')

def evm(code):
    success = True
    ctx = Context(code)

    while ctx.pc < len(code):
        op = code[ctx.pc]
        opcodeObj = opcode.get(op)
        if opcodeObj:
            prehook(opcodeObj)
            opcodeObj.run(ctx)
        else:
            print("Opcode implementation not found for ", hex(op))
            # return fake success but empty stack so that test case
            # panics with proper test name and error message
            return (success, [])
        # pc will always increment by 1 here
        # pc can also be incremented in PUSH opcodes
        ctx.pc += 1
        

    return (success, ctx.stack.list)

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
            (success, stack) = evm(code)

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
    test()
