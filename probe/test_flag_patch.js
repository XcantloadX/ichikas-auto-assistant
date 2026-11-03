'use strict';
// 测试 ticket 注册表的 valid 标志并尝试 patch
const TABLE_B = ptr('0x788f4b750078');
const STRIDE = 16512; // 129 * 128

function flagAddr(ticket) {
    return TABLE_B.add(ticket * STRIDE - 0x4054);
}

// 读最近创建的几个 ticket 的标志
const report = {};
for (const ticket of [0x53, 0x54, 0x55, 0x56, 0x5c, 0x52, 0x50]) {
    try {
        const a = flagAddr(ticket);
        const v = a.readU32();
        report['0x' + ticket.toString(16)] = { at: String(a), flag: v };
    } catch (e) {
        report['0x' + ticket.toString(16)] = String(e).slice(0, 50);
    }
}
console.log(JSON.stringify(report, null, 1));
send({ report: report });

// 尝试把 0x53 的标志写 1，然后调用
const fa = flagAddr(0x53);
fa.writeU32(1);
console.log('flag patched to 1');

const itf = Module.getExportByName('libhoudini.so', 'NativeBridgeItf');
const pGetTrampoline = itf.add(24).readPointer();
const getTrampolineFn = new NativeFunction(pGetTrampoline, 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);
const t = getTrampolineFn(ptr(0), Memory.allocUtf8String('il2cpp_domain_get'), Memory.allocUtf8String('L'), 1, 0);
console.log('tramp:', t);
if (!t.isNull()) {
    // 读取 trampoline 的 ticket
    const arr = Array.from(new Uint8Array(t.readByteArray(4)));
    const ticket = arr[0] | (arr[1] << 8) | (arr[2] << 16) | (arr[3] << 24);
    console.log('new ticket:', '0x' + ticket.toString(16));
    const newFlag = flagAddr(ticket).readU32();
    console.log('new ticket flag:', newFlag);
    // patch 新 ticket 的标志
    flagAddr(ticket).writeU32(1);
    const dg = new NativeFunction(t, 'pointer', []);
    try {
        const d = dg();
        console.log('domain =', d);
        send({ ok: true, domain: String(d), ticket: ticket, oldFlags: report });
    } catch (e) {
        console.log('call err:', e);
        send({ ok: false, err: String(e), ticket: ticket });
    }
}
