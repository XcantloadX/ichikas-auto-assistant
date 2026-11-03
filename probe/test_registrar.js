// 实验 32：① diff ticket 记录 ② 扫描 houdini 代码找记录写入者（含 -0x4054 disp 的指令）
'use strict';

const itf = Process.findModuleByName('libhoudini.so').getExportByName('NativeBridgeItf');
const pLoadLibExt = itf.add(0x70).readPointer();
const loadLibraryExt = new NativeFunction(pLoadLibExt, 'pointer', ['pointer', 'int', 'pointer']);
const IL2CPP = '/data/app/~~_AKbb6cXWFMNLiugNkCZ2g==/com.sega.pjsekai-iMjlP6Bt2jE7PmZPtB4dKA==/lib/arm64/libil2cpp.so';
const handle = loadLibraryExt(Memory.allocUtf8String(IL2CPP), 2, ptr(0));
console.log('handle:', handle);

const pGetTrampoline = itf.add(0x18).readPointer();
const getTrampolineFn = new NativeFunction(pGetTrampoline, 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);

// 我的 ticket
const t = getTrampolineFn(handle, Memory.allocUtf8String('il2cpp_domain_get'), Memory.allocUtf8String('L'), 1, 0);
const arr = Array.from(new Uint8Array(t.readByteArray(24)));
function rd(off) { let v = 0n; for (let k = off + 7; k >= off; k--) v = (v << 8n) | BigInt(arr[k]); return v; }
const myTicket = Number(rd(2));

// TABLE_B：动态从 gateway→resolver→lookup 链解析
const gw = ptr('0x' + rd(12).toString(16));
function callTarget(addr, off) {
    const b = Array.from(new Uint8Array(addr.add(off).readByteArray(5)));
    let rel = b[1] | (b[2] << 8) | (b[3] << 16) | (b[4] << 24);
    if (rel > 0x7fffffff) rel -= 0x100000000;
    return addr.add(off + 5 + rel);
}
const gwb = Array.from(new Uint8Array(gw.readByteArray(0x60)));
let resolver = null;
for (let off = 0x30; off < 0x50; off++) if (gwb[off] === 0xe8) { resolver = callTarget(gw, off); break; }
const resb = Array.from(new Uint8Array(resolver.readByteArray(0x40)));
let lookup = null;
for (let off = 0x20; off < 0x38; off++) if (resb[off] === 0xe8) { lookup = callTarget(resolver, off); break; }
const code = Array.from(new Uint8Array(lookup.readByteArray(0x60)));
let TABLE = null;
for (let i = 0; i < 0x50; i++) {
    if (code[i] === 0x4c && code[i + 1] === 0x8d && code[i + 2] === 0x25) {
        let disp = code[i + 3] | (code[i + 4] << 8) | (code[i + 5] << 16) | (code[i + 6] << 24);
        if (disp > 0x7fffffff) disp -= 0x100000000;
        TABLE = lookup.add(i + 7 + disp); break;
    }
}
console.log('lookup:', lookup, 'TABLE:', TABLE, 'myTicket:', myTicket);
const STRIDE = 16512;

// ① 记录对比（record base = TABLE + ticket*STRIDE - 0x4000，flag 在 -0x54）
function recBase(tk) { return TABLE.add(tk * STRIDE - 0x4000); }
function dumpRec(name, tk) {
    const R = recBase(tk);
    const head = R.readByteArray(0x60);
    const flag = R.sub(0x54).readU32();
    console.log(name + ' ticket=' + tk + ' flag=' + flag + ' head64: ' +
        Array.from(new Uint8Array(head)).map(b => b.toString(16).padStart(2, '0')).join(' '));
}
try { dumpRec('HEALTHY', 1); } catch (e) { console.log('t1 err', e); }
try { dumpRec('MINE', myTicket); } catch (e) { console.log('mine err', e); }

// ② 扫描 houdini 可执行段找含 disp -0x4054 (0xFFFFBFAC) 的代码位置
const mod = Process.findModuleByName('libhoudini.so');
const hits = [];
for (const r of mod.enumerateRanges('r-x')) {
    const matches = Memory.scanSync(r.base, r.size, 'ac bf ff ff');
    for (const m of matches) hits.push(String(m.address));
}
console.log('-0x4054 disp code hits:', hits.length);
send({ hits: hits, myTicket: myTicket, table: String(TABLE) });
