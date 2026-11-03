// 实验 2（从文件加载，避免 heredoc 转义问题）：NativeFunction 调用 arm64 il2cpp_domain_get
'use strict';
const baseStr = __baseAddr__;
console.log('base =', baseStr);
const base = ptr(baseStr);
const fn = base.add(0x49c74e4);
console.log('fn =', fn);
try {
    const bytes = fn.readByteArray(16);
    console.log('bytes:', Array.from(new Uint8Array(bytes)).map(b => b.toString(16).padStart(2, '0')).join(' '));
} catch (e) {
    console.log('read failed:', e);
}
try {
    const domainGet = new NativeFunction(fn, 'pointer', []);
    const dom = domainGet();
    console.log('il2cpp_domain_get() =', dom);
    send({ callOk: true, domain: String(dom) });
} catch (e) {
    console.log('call failed:', e);
    send({ callOk: false, err: String(e) });
}
