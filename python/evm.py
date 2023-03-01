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
from eth_utils import keccak
from typing import Any
from enum import Enum

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
        self.size = 0

    #Internal function
    def _expand(self, offset, dataSize):
        if offset+dataSize > self.size:
            offset = ((((offset+dataSize)-1) // 32) * 32)
            self.array[self.size:offset+32] = bytes(offset + 32 - self.size)
            self.size = len(self.array)

    # Store can be 1 or 32 or "x" bytes dataSize
    def store(self, offset, data, dataSize):
        self._expand(offset, dataSize)
        data = data.to_bytes(dataSize, 'big')
        self.array[offset:offset+dataSize] = data

    def load(self, offset, dataSize=32):
        self._expand(offset, dataSize)
        data = self.array[offset:offset+dataSize]
        data = int.from_bytes(data, "big")
        return data

@dataclass
class Account:
    balance:int
    codeAsm:str
    codeBin:str

@dataclass
class Logs:
    address:str
    data:str
    topics:list[str]

class Storage:
    def __init__(self):
        self.dict = {}

    def store(self, key, value):
        if key > UINT256MAX or value > UINT256MAX:
            print('STACK OVERFLOW')
        else:
            self.dict[key] = value

    def load(self, key):
        if key in self.dict:
            return self.dict[key]
        else:
            return 0

class Context:
    def __init__(self, code, pc=0, calldata = "", jumpDest=[], storage=None):
        self.stack = Stack(1024)
        self.memory = Memory()
        self.code = code
        self.pc = pc
        self.jumpDest = jumpDest
        self.storage = storage
        self.calldata = calldata

class Utils:
    @staticmethod
    def convert2sComplementToInt(a):
        # if MSB (255th bit since its 32 bytes word) is 1,
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

def opcodeStop(ctx, inputParam):
    return OpcodeResponse(success=True, stopRun=True, data=None)

def opcodePush(ctx, inputParam):
    data = 0
    pushBytes = inputParam.Opcode - 0x60 + 1
    for i in range(pushBytes):
        # Big Endian
        data = (data << 8) | ctx.code[ctx.pc]
        ctx.pc +=1
    ctx.stack.push(data)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodePop(ctx, inputParam):
    data = ctx.stack.pop()
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeAdd(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = (a+b)
    # overflow condition
    result &= UINT256MAX
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeMul(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = (a*b)
    # overflow condition
    result &= UINT256MAX
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSub(ctx, inputParam):
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

def opcodeDiv(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    # Handle Divide by 0
    if b == 0:
        result = 0
    else:
        result = int(a / b)
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeMod(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    if b == 0:
        result = 0
    else:
        result = a % b
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeAddMod(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = a+b
    c = ctx.stack.pop()
    result = result % c
    result &= UINT256MAX
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeMulMod(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = a*b
    c = ctx.stack.pop()
    result = result % c
    result &= UINT256MAX
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeExp(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = a ** b
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSignExt(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = b
    mask = (a+1)*8
    if b & int(2**(mask-1)):
        result = (UINT256MAX << mask) | b
        result &= UINT256MAX
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSdiv(ctx, inputParam):
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

def opcodeSmod(ctx, inputParam):
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

def opcodeLT(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    if a < b:
        result = 1
    else:
        result = 0
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeGT(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    if a > b:
        result = 1
    else:
        result = 0
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSLT(ctx, inputParam):
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

def opcodeSGT(ctx, inputParam):
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

def opcodeEQ(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    if a == b:
        result = 1
    else:
        result = 0
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeIsZero(ctx, inputParam):
    a = ctx.stack.pop()
    result = 0
    if a == 0:
        result = 1
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeNot(ctx, inputParam):
    a = ctx.stack.pop()
    a ^= UINT256MAX
    ctx.stack.push(a)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeAnd(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = a & b
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeOr(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = a | b
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeXor(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    result = a ^ b
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSHL(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    if a > 255:
        result = 0
    else:
        result = b << a
        result &= UINT256MAX
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSHR(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    if a > 255:
        result = 0
    else:
        result = b >> a
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSAR(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    isNegative = b & (1 << 255)
    if a > 255:
        if isNegative:
            result = UINT256MAX
        else:
            result = 0
    else:
        result = b >> a
        if isNegative:
            for i in range(a):
                result |= ( 1 << (255-i))
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeByte(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()

    if a > 31:
        result = 0
    else:
        offset = (31 - a) * 8
        result = (b & (0xff << offset)) >> offset
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeDup(ctx, inputParam):
    index = inputParam.Opcode - 0x80 + 1
    try:
        a = ctx.stack.peek(-index)
    except IndexError:
        print("Not enough values on the stack")
        return OpcodeResponse(success=False, stopRun=True, data=None)
    ctx.stack.push(a)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSwap(ctx, inputParam):
    index = inputParam.Opcode - 0x90 + 1
    try:
        bottom = ctx.stack.peek(-(index+1))
    except IndexError:
        print("Not enough values on the stack")
        return OpcodeResponse(success=False, stopRun=True, data=None)
    ctx.stack.replace(-(index+1), ctx.stack.peek(-1))
    ctx.stack.replace(-1, bottom)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeInvalid(ctx, inputParam):
    # Consume all gas, Sorry !
    return OpcodeResponse(success=False, stopRun=True, data=None)

def opcodePC(ctx, inputParam):
    # Already increment PC before, return PC - 1
    ctx.stack.push(ctx.pc - 1)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeGas(ctx, inputParam):
    # not implemented, return UINTMAX
    ctx.stack.push(UINT256MAX)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeJump(ctx, inputParam):
    a = ctx.stack.pop()
    # jump pc should be JUMPDEST
    if a not in ctx.jumpDest:
        return OpcodeResponse(success=False, stopRun=True, data=None)
    else:
        ctx.pc = a+1
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeJumpI(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    if b > 0:
        # jump pc should be JUMPDEST
        if a not in ctx.jumpDest:
            return OpcodeResponse(success=False, stopRun=True, data=None)
        else:
            ctx.pc = a
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeJumpDest(ctx, inputParam):
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeMstore(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    ctx.memory.store(a, b, 32)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeMload(ctx, inputParam):
    a = ctx.stack.pop()
    data = ctx.memory.load(a)
    ctx.stack.push(data)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeMstore8(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop() & 0xff
    ctx.memory.store(a, b, 1)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeMsize(ctx, inputParam):
    ctx.stack.push(ctx.memory.size)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSha3(ctx, inputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    data = ctx.memory.load(a)
    b *= 8
    data >>= (256-b)
    ctx.stack.push(int.from_bytes(keccak(data), "big"))
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeAddress(ctx, inputParam):
    ctx.stack.push(int(inputParam.Txn['to'], 16))
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeCaller(ctx, inputParam):
    ctx.stack.push(int(inputParam.Txn['from'], 16))
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeOrigin(ctx, inputParam):
    ctx.stack.push(int(inputParam.Txn['origin'], 16))
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeGasPrice(ctx, inputParam):
    ctx.stack.push(int(inputParam.Txn['gasprice'], 16))
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeBaseFee(ctx, inputParam):
    ctx.stack.push(int(inputParam.Block['basefee'], 16))
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeCoinbase(ctx, inputParam):
    ctx.stack.push(int(inputParam.Block['coinbase'], 16))
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeTimestamp(ctx, inputParam):
    ctx.stack.push(int(inputParam.Block['timestamp'], 16))
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeNumber(ctx, inputParam):
    ctx.stack.push(int(inputParam.Block['number'], 16))
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeDifficulty(ctx, inputParam):
    ctx.stack.push(int(inputParam.Block['difficulty'], 16))
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeGasLimit(ctx, inputParam):
    ctx.stack.push(int(inputParam.Block['gaslimit'], 16))
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeChainId(ctx, inputParam):
    ctx.stack.push(int(inputParam.Block['chainid'], 16))
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeBlockHash(ctx, inputParam):
    # Not Implemented.
    ctx.stack.push(0)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeBalance(ctx, inputParam):
    a = ctx.stack.pop()
    if a not in inputParam.State:
        result = 0
    else:
        result = inputParam.State[a].balance
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeCallValue(ctx, inputParam):
    ctx.stack.push(int(inputParam.Txn['value'], 16))
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeCallDataLoad(ctx, inputParam):
    calldataOrig = ctx.calldata
    a = ctx.stack.pop()
    calldata = calldataOrig[a*2:a*2+64]
    calldata = int(calldata, 16)
    if (a*2)+64 > len(calldataOrig):
        calldata <<= (((a*2)+64-len(calldataOrig))//2)*8
    ctx.stack.push(calldata)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeCallDataSize(ctx, inputParam):
    calldata = ctx.calldata
    ctx.stack.push(len(calldata)//2)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeCallDataCopy(ctx, inputParam):
    calldataOrig = ctx.calldata
    # destOffset in memory
    a = ctx.stack.pop()
    # offset in calldata
    b = ctx.stack.pop()
    # size
    c = ctx.stack.pop()
    calldata = calldataOrig[b*2:b*2+(c*2)]
    calldata = int(calldata, 16)
    if (b*2)+(c*2) > len(calldataOrig):
        calldata <<= (((b*2)+(c*2)-len(calldataOrig))//2)*8
    ctx.memory.store(a, calldata, c)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeCodeCopy(ctx, inputParam):
    code = ctx.code
    # destOffset in memory
    a = ctx.stack.pop()
    # offset in executing code, can be calldata if deploying code.
    #ToDo : code in calldata not implemented.
    b = ctx.stack.pop()
    # size
    c = ctx.stack.pop()
    codeLen = len(code)
    code = code[b:b+c]
    code = int.from_bytes(code, "big")
    if b+c > codeLen:
        code <<= (b + c - codeLen)*8
    ctx.memory.store(a, code, c)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeCodeSize(ctx, inputParam):
    ctx.stack.push(len(ctx.code))
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeExtCodeSize(ctx, inputParam):
    a = ctx.stack.pop()
    result = 0
    if a in inputParam.State and inputParam.State[a].codeBin:
        result = len(inputParam.State[a].codeBin) // 2
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeExtCodeCopy(ctx, inputParam):
    address = ctx.stack.pop()
    code = inputParam.State[address].codeBin
    # destOffset in memory
    a = ctx.stack.pop()
    # offset in calldata
    b = ctx.stack.pop()
    # size
    c = ctx.stack.pop()
    codeExact = code[b*2:b*2+(c*2)]
    codeExact = int(codeExact, 16)
    if (b*2)+(c*2) > len(code):
        codeExact <<= (((b*2)+(c*2)-len(code))//2)*8
    ctx.memory.store(a, codeExact, c)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeExtCodeHash(ctx, inputParam):
    a = ctx.stack.pop()
    result = 0
    if a in inputParam.State and inputParam.State[a].codeBin:
        result = keccak(int(inputParam.State[a].codeBin, 16))
        result = int.from_bytes(result, "big")
        #ToDo : If codeBin is not present, then hash value will be
        #       0xc5d24601...
    print(result)
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSelfBalance(ctx, inputParam):
    address = inputParam.Txn["to"]
    address = int(address, 16)
    result = 0
    if address in inputParam.State and inputParam.State[address].balance:
        result = inputParam.State[address].balance
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSStore(ctx, InputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    ctx.storage.store(a, b)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeSLoad(ctx, InputParam):
    a = ctx.stack.pop()
    result = ctx.storage.load(a)
    ctx.stack.push(result)
    return OpcodeResponse(success=True, stopRun=False, data=None)

def opcodeLog(ctx, InputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    numTopics = InputParam.Opcode - 0xa0
    topics = []
    for _ in range(numTopics):
        c = ctx.stack.pop()
        topics.append(hex(c))
    data = hex(ctx.memory.load(a, b))
    data = data[2:]
    logs = Logs(InputParam.Txn['to'], data, topics)
    return OpcodeResponse(success=True, stopRun=False, data={'logs':logs})

def opcodeReturn(ctx, InputParam):
    a = ctx.stack.pop()
    b = ctx.stack.pop()
    data = hex(ctx.memory.load(a, b))
    data = data[2:]
    return OpcodeResponse(success=True, stopRun=False, data={'returnData':data})

@dataclass
class OpcodeResponse:
    success: bool
    stopRun: bool #stop will be True for stop opcode
    data: dict

@dataclass
class OpcodeData:
    opcode:int
    name:str
    # function pointer
    run:any

@dataclass
class InputParam:
    Opcode: int
    Txn: dict
    Block: dict
    State: dict

opcode = {}
opcode[0x00] = OpcodeData(0x00, "STOP", opcodeStop)
opcode[0x60] = OpcodeData(0x60, "PUSH1", opcodePush)
opcode[0x61] = OpcodeData(0x61, "PUSH2", opcodePush)
opcode[0x62] = OpcodeData(0x62, "PUSH3", opcodePush)
opcode[0x63] = OpcodeData(0x63, "PUSH4", opcodePush)
opcode[0x64] = OpcodeData(0x64, "PUSH5", opcodePush)
opcode[0x65] = OpcodeData(0x65, "PUSH6", opcodePush)
opcode[0x66] = OpcodeData(0x66, "PUSH7", opcodePush)
opcode[0x67] = OpcodeData(0x67, "PUSH8", opcodePush)
opcode[0x68] = OpcodeData(0x68, "PUSH9", opcodePush)
opcode[0x69] = OpcodeData(0x69, "PUSH10", opcodePush)
opcode[0x6A] = OpcodeData(0x6A, "PUSH11", opcodePush)
opcode[0x6B] = OpcodeData(0x6B, "PUSH12", opcodePush)
opcode[0x6C] = OpcodeData(0x6C, "PUSH13", opcodePush)
opcode[0x6D] = OpcodeData(0x6D, "PUSH14", opcodePush)
opcode[0x6E] = OpcodeData(0x6E, "PUSH15", opcodePush)
opcode[0x6F] = OpcodeData(0x6F, "PUSH16", opcodePush)
opcode[0x70] = OpcodeData(0x70, "PUSH17", opcodePush)
opcode[0x71] = OpcodeData(0x71, "PUSH18", opcodePush)
opcode[0x72] = OpcodeData(0x72, "PUSH19", opcodePush)
opcode[0x73] = OpcodeData(0x73, "PUSH20", opcodePush)
opcode[0x74] = OpcodeData(0x74, "PUSH21", opcodePush)
opcode[0x75] = OpcodeData(0x75, "PUSH22", opcodePush)
opcode[0x76] = OpcodeData(0x76, "PUSH23", opcodePush)
opcode[0x77] = OpcodeData(0x77, "PUSH24", opcodePush)
opcode[0x78] = OpcodeData(0x78, "PUSH25", opcodePush)
opcode[0x79] = OpcodeData(0x79, "PUSH26", opcodePush)
opcode[0x7A] = OpcodeData(0x7A, "PUSH27", opcodePush)
opcode[0x7B] = OpcodeData(0x7B, "PUSH28", opcodePush)
opcode[0x7C] = OpcodeData(0x7C, "PUSH29", opcodePush)
opcode[0x7D] = OpcodeData(0x7D, "PUSH30", opcodePush)
opcode[0x7E] = OpcodeData(0x7E, "PUSH31", opcodePush)
opcode[0x7F] = OpcodeData(0x7F, "PUSH32", opcodePush)
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
opcode[0x80] = OpcodeData(0x80, "DUP1", opcodeDup)
opcode[0x81] = OpcodeData(0x81, "DUP2", opcodeDup)
opcode[0x82] = OpcodeData(0x82, "DUP3", opcodeDup)
opcode[0x83] = OpcodeData(0x83, "DUP4", opcodeDup)
opcode[0x84] = OpcodeData(0x84, "DUP5", opcodeDup)
opcode[0x85] = OpcodeData(0x85, "DUP6", opcodeDup)
opcode[0x86] = OpcodeData(0x86, "DUP7", opcodeDup)
opcode[0x87] = OpcodeData(0x87, "DUP8", opcodeDup)
opcode[0x88] = OpcodeData(0x88, "DUP9", opcodeDup)
opcode[0x89] = OpcodeData(0x89, "DUP10", opcodeDup)
opcode[0x8a] = OpcodeData(0x8a, "DUP11", opcodeDup)
opcode[0x8b] = OpcodeData(0x8b, "DUP12", opcodeDup)
opcode[0x8c] = OpcodeData(0x8c, "DUP13", opcodeDup)
opcode[0x8d] = OpcodeData(0x8d, "DUP14", opcodeDup)
opcode[0x8e] = OpcodeData(0x8e, "DUP15", opcodeDup)
opcode[0x8f] = OpcodeData(0x8f, "DUP16", opcodeDup)
opcode[0x90] = OpcodeData(0x90, "SWAP1", opcodeSwap)
opcode[0x91] = OpcodeData(0x91, "SWAP2", opcodeSwap)
opcode[0x92] = OpcodeData(0x92, "SWAP3", opcodeSwap)
opcode[0x93] = OpcodeData(0x93, "SWAP4", opcodeSwap)
opcode[0x94] = OpcodeData(0x94, "SWAP5", opcodeSwap)
opcode[0x95] = OpcodeData(0x95, "SWAP6", opcodeSwap)
opcode[0x96] = OpcodeData(0x96, "SWAP7", opcodeSwap)
opcode[0x97] = OpcodeData(0x97, "SWAP8", opcodeSwap)
opcode[0x98] = OpcodeData(0x98, "SWAP9", opcodeSwap)
opcode[0x99] = OpcodeData(0x99, "SWAP10", opcodeSwap)
opcode[0x9a] = OpcodeData(0x9a, "SWAP11", opcodeSwap)
opcode[0x9b] = OpcodeData(0x9b, "SWAP12", opcodeSwap)
opcode[0x9c] = OpcodeData(0x9c, "SWAP13", opcodeSwap)
opcode[0x9d] = OpcodeData(0x9d, "SWAP14", opcodeSwap)
opcode[0x9e] = OpcodeData(0x9e, "SWAP15", opcodeSwap)
opcode[0x9f] = OpcodeData(0x9f, "SWAP16", opcodeSwap)
opcode[0xfe] = OpcodeData(0xfe, "INVALID", opcodeInvalid)
opcode[0x58] = OpcodeData(0x58, "PC", opcodePC)
opcode[0x5a] = OpcodeData(0x5a, "GAS", opcodeGas)
opcode[0x56] = OpcodeData(0x56, "JUMP", opcodeJump)
opcode[0x57] = OpcodeData(0x57, "JUMPI", opcodeJumpI)
opcode[0x5B] = OpcodeData(0x57, "JUMPDEST", opcodeJumpDest)
opcode[0x52] = OpcodeData(0x52, "MSTORE", opcodeMstore)
opcode[0x52] = OpcodeData(0x52, "MSTORE", opcodeMstore)
opcode[0x51] = OpcodeData(0x51, "MLOAD", opcodeMload)
opcode[0x53] = OpcodeData(0x52, "MSTORE8", opcodeMstore8)
opcode[0x59] = OpcodeData(0x59, "MSIZE", opcodeMsize)
opcode[0x20] = OpcodeData(0x20, "SHA3", opcodeSha3)
opcode[0x30] = OpcodeData(0x30, "ADDRESS", opcodeAddress)
opcode[0x33] = OpcodeData(0x33, "CALLER", opcodeCaller)
opcode[0x32] = OpcodeData(0x32, "ORIGIN", opcodeOrigin)
opcode[0x3a] = OpcodeData(0x3a, "GASPRICE", opcodeGasPrice)
opcode[0x48] = OpcodeData(0x48, "BASEFEE", opcodeBaseFee)
opcode[0x41] = OpcodeData(0x41, "COINBASE", opcodeCoinbase)
opcode[0x42] = OpcodeData(0x42, "TIMESTAMP", opcodeTimestamp)
opcode[0x43] = OpcodeData(0x43, "NUMBER", opcodeNumber)
opcode[0x44] = OpcodeData(0x44, "DIFFICULTY", opcodeDifficulty)
opcode[0x45] = OpcodeData(0x45, "DIFFICULTY", opcodeGasLimit)
opcode[0x46] = OpcodeData(0x46, "CHAINID", opcodeChainId)
opcode[0x40] = OpcodeData(0x40, "BLOCKHASH", opcodeBlockHash)
opcode[0x31] = OpcodeData(0x31, "BALANCE", opcodeBalance)
opcode[0x34] = OpcodeData(0x34, "CALLVALUE", opcodeCallValue)
opcode[0x35] = OpcodeData(0x35, "CALLDATALOAD", opcodeCallDataLoad)
opcode[0x36] = OpcodeData(0x36, "CALLDATASIZE", opcodeCallDataSize)
opcode[0x37] = OpcodeData(0x37, "CALLDATACOPY", opcodeCallDataCopy)
opcode[0x38] = OpcodeData(0x38, "CODESIZE", opcodeCodeSize)
opcode[0x39] = OpcodeData(0x39, "CODECOPY", opcodeCodeCopy)
opcode[0x3b] = OpcodeData(0x3b, "EXTCODESIZE", opcodeExtCodeSize)
opcode[0x3c] = OpcodeData(0x3c, "EXTCODECOPY", opcodeExtCodeCopy)
opcode[0x3f] = OpcodeData(0x3f, "EXTCODEHASH", opcodeExtCodeHash)
opcode[0x47] = OpcodeData(0x47, "SELFBALANCE", opcodeSelfBalance)
opcode[0x55] = OpcodeData(0x55, "SSTORE", opcodeSStore)
opcode[0x54] = OpcodeData(0x54, "SLOAD", opcodeSLoad)
opcode[0xa0] = OpcodeData(0xa0, "LOG0", opcodeLog)
opcode[0xa1] = OpcodeData(0xa1, "LOG1", opcodeLog)
opcode[0xa2] = OpcodeData(0xa2, "LOG2", opcodeLog)
opcode[0xa3] = OpcodeData(0xa3, "LOG3", opcodeLog)
opcode[0xa4] = OpcodeData(0xa4, "LOG4", opcodeLog)
opcode[0xf3] = OpcodeData(0xf3, "RETURN", opcodeReturn)

def prehook(opcodeDataObj):
    print(f'Running opcode {hex(opcodeDataObj.opcode)} {opcodeDataObj.name}')

class outputStackFormat(Enum):
    MultipleLine = 1
    SingleLine = 2

def evm(code, outStackFormat, tx, block, state):
    global testsRun, testsMax
    if testsRun >= testsMax:
        print(f'Implemented {len(opcode)} opcodes ')
        sys.exit()
    testsRun+=1

    success = True
    jumpDest = Utils.scanForJumpDest(code)
    storage = Storage()
    calldata = tx.get('data', "") if tx else ""
    ctx = Context(code, calldata=calldata, jumpDest=jumpDest, storage=storage)
    # Create state
    stateDict = {}
    for address, values in state.items():
        stateDict[int(address,16)] = Account(None, None, None)
        if 'balance' in values:
            stateDict[int(address,16)].balance = int(values['balance'], 16)
        if 'code' in values:
            stateDict[int(address,16)].codeAsm = values['code']['asm']
            stateDict[int(address,16)].codeBin = values['code']['bin']

    inputParam = InputParam(Opcode=None, Txn=tx, Block=block, State=stateDict)

    while ctx.pc < len(code):
        op = code[ctx.pc]
        # pc will always increment by 1 here
        # pc can also be incremented in PUSH opcodes
        ctx.pc += 1
        opcodeDataObj = opcode.get(op)
        if opcodeDataObj:
            prehook(opcodeDataObj)
            # Use the same object for all opcodes, so txn etc will be retained
            inputParam.Opcode = opcodeDataObj.opcode
            opcodeReturn = opcodeDataObj.run(ctx, inputParam)
            success = opcodeReturn.success
            if opcodeReturn.stopRun == True:
                break
        else:
            print("Opcode implementation not found for ", hex(op))
            # return fake success but empty stack and logs so that test case
            # panics with proper test name and error message
            return (True, [], None)

    stackOutput=[]
    logsReturnOutput = {}
    if opcodeReturn.data:
        if 'logs' in opcodeReturn.data:
            to = opcodeReturn.data['logs'].address
            data = opcodeReturn.data['logs'].data
            topics = opcodeReturn.data['logs'].topics
            logs = []
            logs.append({'address':to, 'data':data, 'topics':topics})
            logsReturnOutput['logs'] = logs
        logsReturnOutput['returnData'] = opcodeReturn.data.get('returnData', None)

    if outStackFormat == outputStackFormat.MultipleLine:
        while ctx.stack.len():
            stackOutput.append(ctx.stack.pop())
    else:
        # Default output stack format is outputStackFormat.SingleLine
        tempList = [f'{i:x}' for i in ctx.stack.elements()]
        print('result in hex ', ''.join(tempList))
        if len(tempList): stackOutput.append(int(''.join(tempList), 16))

    return (success, stackOutput, logsReturnOutput)

def test():
    script_dirname = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_dirname, "..", "evm.json")
    with open(json_file) as f:
        data = json.load(f)
        total = len(data)

        for i, test in enumerate(data):
            # Note: as the test cases get more complex, you'll need to modify this
            # to pass down more arguments to the evm function
            tx = test.get('tx', None)
            block = test.get('block', None)
            state = test.get('state', {})

            code = bytes.fromhex(test['code']['bin'])

            testStackFormat = test['expect'].get('stack', [])
            if len(testStackFormat) > 1:
                testStackFormat = outputStackFormat.MultipleLine
            else:
                testStackFormat = outputStackFormat.SingleLine

            (success, stack, logsReturnOutput) = evm(code, testStackFormat, tx, block, state)

            logOutput = test['expect'].get('logs', None)
            returnOutput = test['expect'].get('return', None)
            if logOutput:
                expectedInput = test['expect']['logs']
                expectedOutput = logsReturnOutput['logs']
                errorFormat = 'Log'
            elif returnOutput:
                expectedInput = test['expect']['return']
                expectedOutput = logsReturnOutput['returnData']
                errorFormat = 'Return Data'
            else:
                expectedInput = [int(x, 16) for x in test['expect']['stack']]
                expectedOutput = stack
                errorFormat = 'Stack'
            
            if expectedOutput != expectedInput or success != test['expect']['success']:
                print(f"❌ Test #{i + 1}/{total} {test['name']}")
                if expectedOutput != expectedInput:
                    print(f"{errorFormat} doesn't match")
                    print(" expected:", expectedInput)
                    print("   actual:", expectedOutput)
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
        evm(bytes.fromhex(singleBin), 1, None, None, {})
