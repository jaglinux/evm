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
            print('STACK OVERFLOW')
            return False
        self.list.append(item)

    def pop(self):
        return self.list.pop()

    def len(self):
        return len(self.list)

    def elements(self):
        return self.list

    def peek(self, index):
        return self.list[index]

    def replace(self, index, value):
        self.list[index] = value

class Memory:
    def __init__(self):
        self.array = bytearray();

class Context:
    def __init__(self, code, pc=0, jumpDest=[]):
        self.stack = Stack(1024)
        self.memory = Memory()
        self.code = code
        self.pc = pc
        self.jumpDest = jumpDest

class Utils:
    @staticmethod
    def convert2sComplementToInt(a):
        # if MSB (256th bit since its 32 bytes word) is 1,
        #  then its negative number
        # if MSB is 0, its positive number, just return the input
        if a & (1 << 255):
            return a - (1 << 256)
        return a

    @staticmethod
    def convertIntTo2sComplement(a):
        # if its +ve integer, just return the input
        # if its -ve integer, calculate 2s Complement
        if a < 0:
            return (1 << 256) + a
        return a

    @staticmethod
    def scanForJumpDest(code):
        result = []
        pc=0
        while pc < len(code):
            currentCode = code[pc]
            if currentCode >= 0x60 and currentCode <=0x7f:
                pc += (currentCode - 0x60)+1
            elif code[pc] == 0x5b:
                result.append(pc)
            pc+=1
        return result

def opcodeStop(ctx, dummy):
    return OpcodeResponse(success=True, stopRun=True, data=None)

def opcodePush(ctx, pushBytes):
    data = 0
    for i in range(pushBytes):
        # Big Endian
        data = (data << 8) | ctx.code[ctx.pc]
        ctx.pc +=1
    ctx.stack.push(data)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodePop(ctx, dummy):
    data = ctx.stack.pop()
    return OpcodeResponse(success=True, stopRun=False, data=data)

def opcodeAdd(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = (a+b)
    # overflow condition
    result &= UINT256MAX
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeMul(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = (a*b)
    # overflow condition
    result &= UINT256MAX
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

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
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeDiv(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    # Handle Divide by 0
    if b == 0:
        result = 0
    else:
        result = int(a / b)
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeMod(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    if b == 0:
        result = 0
    else:
        result = a % b
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeAddMod(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = a+b
    c = ctx.stack.pop()
    result = result % c
    result &= UINT256MAX
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeMulMod(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = a*b
    c = ctx.stack.pop()
    result = result % c
    result &= UINT256MAX
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeExp(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = a ** b
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSignExt(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = b
    mask = (a+1)*8
    if b & int(2**(mask-1)):
        result = (UINT256MAX << mask) | b
        result &= UINT256MAX
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSdiv(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    # Inputs are in 2s complement, Get the corresponding int value
    a = Utils.convert2sComplementToInt(a)
    b = Utils.convert2sComplementToInt(b)
    if b == 0:
        result = 0
    else:
        result = a // b
        # Result is int. If its -ve integer, Get the corresponding
        # 2s complement
        result = Utils.convertIntTo2sComplement(result)
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSmod(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    # Inputs are in 2s complement, Get the corresponding int value
    a = Utils.convert2sComplementToInt(a)
    b = Utils.convert2sComplementToInt(b)
    if b == 0:
        result = 0
    else:
        result = a % b
        # Result is int. If its -ve integer, Get the corresponding
        # 2s complement
        result = Utils.convertIntTo2sComplement(result)
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeLT(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    if a < b:
        result = 1
    else:
        result = 0
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeGT(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    if a > b:
        result = 1
    else:
        result = 0
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSLT(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    a = Utils.convert2sComplementToInt(a)
    b = Utils.convert2sComplementToInt(b)
    if a < b:
        result = 1
    else:
        result = 0
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSGT(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    a = Utils.convert2sComplementToInt(a)
    b = Utils.convert2sComplementToInt(b)
    if a > b:
        result = 1
    else:
        result = 0
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeEQ(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    if a == b:
        result = 1
    else:
        result = 0
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeIsZero(ctx, dummy):
    a = ctx.stack.pop()
    result = 0
    if a == 0:
        result = 1
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeNot(ctx, dummy):
    a = ctx.stack.pop()
    a ^= (2 ** 256)-1
    ctx.stack.push(a)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeAnd(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = a & b
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeOr(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = a | b
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeXor(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = a ^ b
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSHL(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    if a > 255:
        result = 0
    else:
        result = b << a
        result &= UINT256MAX
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSHR(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    if a > 255:
        result = 0
    else:
        result = b >> a
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSAR(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    isNegative = b & (1 << 255)
    if a > 255:
        if isNegative:
            result = (2**256)-1
        else:
            result = 0
    else:
        result = b >> a
        if isNegative:
            for i in range(a):
                result |= ( 1 << (255-i))
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeByte(ctx, dummy):
    a = ctx.stack.pop()
    b = ctx.stack.pop()

    if a > 31:
        result = 0
    else:
        offset = (31 - a) * 8
        result = (b & (0xff << offset)) >> offset
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeDup(ctx, index):
    try:
        a = ctx.stack.peek(-index)
    except IndexError:
        print("Not enough values on the stack")
        return OpcodeResponse(success=False, stopRun=True, data=None)
    ctx.stack.push(a)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSwap(ctx, index):
    try:
        bottom = ctx.stack.peek(-(index+1))
    except IndexError:
        print("Not enough values on the stack")
        return OpcodeResponse(success=False, stopRun=True, data=None)
    ctx.stack.replace(-(index+1), ctx.stack.peek(-1))
    ctx.stack.replace(-1, bottom)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeInvalid(ctx, dummy):
    # Consume all gas, Sorry !
    return OpcodeResponse(success=False, stopRun=True, data=None)

def opcodePC(ctx, dummy):
    # Already increment PC before, return PC - 1
    ctx.stack.push(ctx.pc - 1)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeGas(ctx, dummy):
    # not implemented, return UINTMAX
    ctx.stack.push(UINT256MAX)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeJump(ctx, dummy):
    a = ctx.stack.pop()
    # jump pc should be JUMPDEST
    if a not in ctx.jumpDest:
        return OpcodeResponse(success=False, stopRun=True, data=None)
    else:
        ctx.pc = a+1
    return OpcodeResponse(success=True, stopRun=False, data=None)

@dataclass
class OpcodeResponse:
    success: bool
    stopRun: bool #stop will be True for stop opcode
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
opcode[0x08] = OpcodeData(0x08, "MODADD", opcodeAddMod)
opcode[0x09] = OpcodeData(0x09, "MODMUL", opcodeMulMod)
opcode[0x0A] = OpcodeData(0x0A, "EXP", opcodeExp)
opcode[0x0B] = OpcodeData(0x0B, "SIGNEXTEND", opcodeSignExt)
opcode[0x05] = OpcodeData(0x05, "SDIV", opcodeSdiv)
opcode[0x07] = OpcodeData(0x07, "SMOD", opcodeSmod)
opcode[0x10] = OpcodeData(0x10, "LT", opcodeLT)
opcode[0x11] = OpcodeData(0x11, "GT", opcodeGT)
opcode[0x12] = OpcodeData(0x12, "SLT", opcodeSLT)
opcode[0x13] = OpcodeData(0x13, "SGT", opcodeSGT)
opcode[0x14] = OpcodeData(0x14, "EQ", opcodeEQ)
opcode[0x15] = OpcodeData(0x15, "ISZERO", opcodeIsZero)
opcode[0x19] = OpcodeData(0x19, "NOT", opcodeNot)
opcode[0x16] = OpcodeData(0x16, "AND", opcodeAnd)
opcode[0x17] = OpcodeData(0x17, "OR", opcodeOr)
opcode[0x18] = OpcodeData(0x18, "XOR", opcodeXor)
opcode[0x1B] = OpcodeData(0x1B, "SHL", opcodeSHL)
opcode[0x1C] = OpcodeData(0x1C, "SHR", opcodeSHR)
opcode[0x1D] = OpcodeData(0x1D, "SAR", opcodeSAR)
opcode[0x1A] = OpcodeData(0x1A, "BYTE", opcodeByte)
opcode[0x80] = OpcodeData(0x80, "DUP1", opcodeDup, 1)
opcode[0x81] = OpcodeData(0x81, "DUP2", opcodeDup, 2)
opcode[0x82] = OpcodeData(0x82, "DUP3", opcodeDup, 3)
opcode[0x83] = OpcodeData(0x83, "DUP4", opcodeDup, 4)
opcode[0x84] = OpcodeData(0x84, "DUP5", opcodeDup, 5)
opcode[0x85] = OpcodeData(0x85, "DUP6", opcodeDup, 6)
opcode[0x86] = OpcodeData(0x86, "DUP7", opcodeDup, 7)
opcode[0x87] = OpcodeData(0x87, "DUP8", opcodeDup, 8)
opcode[0x88] = OpcodeData(0x88, "DUP9", opcodeDup, 9)
opcode[0x89] = OpcodeData(0x89, "DUP10", opcodeDup, 10)
opcode[0x8a] = OpcodeData(0x8a, "DUP11", opcodeDup, 11)
opcode[0x8b] = OpcodeData(0x8b, "DUP12", opcodeDup, 12)
opcode[0x8c] = OpcodeData(0x8c, "DUP13", opcodeDup, 13)
opcode[0x8d] = OpcodeData(0x8d, "DUP14", opcodeDup, 14)
opcode[0x8e] = OpcodeData(0x8e, "DUP15", opcodeDup, 15)
opcode[0x8f] = OpcodeData(0x8f, "DUP16", opcodeDup, 16)
opcode[0x90] = OpcodeData(0x90, "SWAP1", opcodeSwap, 1)
opcode[0x91] = OpcodeData(0x91, "SWAP2", opcodeSwap, 2)
opcode[0x92] = OpcodeData(0x92, "SWAP3", opcodeSwap, 3)
opcode[0x93] = OpcodeData(0x93, "SWAP4", opcodeSwap, 4)
opcode[0x94] = OpcodeData(0x94, "SWAP5", opcodeSwap, 5)
opcode[0x95] = OpcodeData(0x95, "SWAP6", opcodeSwap, 6)
opcode[0x96] = OpcodeData(0x96, "SWAP7", opcodeSwap, 7)
opcode[0x97] = OpcodeData(0x97, "SWAP8", opcodeSwap, 8)
opcode[0x98] = OpcodeData(0x98, "SWAP9", opcodeSwap, 9)
opcode[0x99] = OpcodeData(0x99, "SWAP10", opcodeSwap, 10)
opcode[0x9a] = OpcodeData(0x9a, "SWAP11", opcodeSwap, 11)
opcode[0x9b] = OpcodeData(0x9b, "SWAP12", opcodeSwap, 12)
opcode[0x9c] = OpcodeData(0x9c, "SWAP13", opcodeSwap, 13)
opcode[0x9d] = OpcodeData(0x9d, "SWAP14", opcodeSwap, 14)
opcode[0x9e] = OpcodeData(0x9e, "SWAP15", opcodeSwap, 15)
opcode[0x9f] = OpcodeData(0x9f, "SWAP16", opcodeSwap, 16)
opcode[0xfe] = OpcodeData(0xfe, "INVALID", opcodeInvalid)
opcode[0x58] = OpcodeData(0x58, "PC", opcodePC)
opcode[0x5a] = OpcodeData(0x5a, "GAS", opcodeGas)
opcode[0x56] = OpcodeData(0x56, "JUMP", opcodeJump)

def prehook(opcodeObj):
    print(f'Running opcode {hex(opcodeObj.opcode)} {opcodeObj.name}')

def evm(code, outputStackLen):
    global testsRun, testsMax
    if testsRun >= testsMax:
        print(f'Implemented {len(opcode)} opcodes ')
        sys.exit()
    testsRun+=1

    success = True
    jumpDest = Utils.scanForJumpDest(code)
    ctx = Context(code, jumpDest=jumpDest)

    while ctx.pc < len(code):
        op = code[ctx.pc]
        # pc will always increment by 1 here
        # pc can also be incremented in PUSH opcodes
        ctx.pc += 1
        opcodeObj = opcode.get(op)
        if opcodeObj:
            prehook(opcodeObj)
            opcodeReturn = opcodeObj.run(ctx, opcodeObj.pushBytes)
            success = opcodeReturn.success
            if opcodeReturn.stopRun == True:
                break
        else:
            print("Opcode implementation not found for ", hex(op))
            # return fake success but empty stack so that test case
            # panics with proper test name and error message
            return (True, [])
        
    result=[]
    if ctx.stack.len():
        if outputStackLen >= 2:
        # output format is different if output stack is greater than 2
        # check evm.json for more details.
            while ctx.stack.len():
                result.append(ctx.stack.pop())
        else:
            tempList = [f'{i:x}' for i in ctx.stack.elements()]
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
