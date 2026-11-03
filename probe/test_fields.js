// 实验 23：从 klass dump 中定位 fields 数组并解码字段偏移
'use strict';

const KLASS = ptr(__KLASS__);
const klassDump = new Uint8Array(__KLASS_DUMP__); // 0x140 bytes

function rdU64(off) {
    // 从 klass 现场内存读（用 dump 里的小端）
    let v = 0n;
    for (let i = 7; i >= 0; i--) v = (v << 8n) | BigInt(klassDump[off + i]);
    return v;
}

// 对 klass 里每个 qword，验证它是否是 fields 数组指针：
// [cand] = P (Il2CppFieldInfo*)，P+0 = char* 名字
const results = [];
for (let off = 0; off + 8 <= klassDump.length; off += 8) {
    const v = rdU64(off);
    if (v < 0x1000n) continue;
    const p = ptr('0x' + v.toString(16));
    let ok = false, firstName = null;
    try {
        const f0 = p.readPointer();           // 第一个 field info
        const namePtr = f0.readPointer();     // char*
        firstName = namePtr.readCString(48);
        ok = firstName !== null && /^[A-Za-z_][A-Za-z0-9_<>.]*$/.test(firstName);
        // 进一步校验第二个字段名也合法
        const f1name = p.add(8).readPointer().readPointer().readCString(48);
        ok = ok && f1name !== null && /^[A-Za-z_][A-Za-z0-9_]*$/.test(f1name);
    } catch (e) { ok = false; }
    if (ok) results.push({ off: off, firstField: firstName });
}
console.log('fields array candidates:', JSON.stringify(results));
send({ fieldsCands: results });

// 取最优候选，解码全部字段
if (results.length > 0) {
    const fieldsPtr = KLASS.add(results[0].off);
    // field count：在 fields 指针附近的 int —— 先扫 fields 指针数组直到非法项
    const fields = [];
    try {
        for (let i = 0; i < 64; i++) {
            const fi = fieldsPtr.readPointer().add(i * 8).readPointer();
            const name = fi.readPointer().readCString(64);
            if (!name || name.length > 100) break;
            const type = fi.add(8).readPointer();
            const parent = fi.add(0x10).readPointer();
            const offset = fi.add(0x18).readS32();
            const token = fi.add(0x1c).readU32();
            fields.push({ name: name, offset: offset, token: '0x' + token.toString(16), parentOk: String(parent) === String(KLASS) });
        }
    } catch (e) { }
    console.log('fields:', JSON.stringify(fields, null, 1));
    send({ fields: fields });
}
