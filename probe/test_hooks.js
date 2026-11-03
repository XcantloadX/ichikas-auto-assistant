// 实验 19：枚举哪些 il2cpp 导出被内联 hook（内存 prologue vs 文件 prologue）
'use strict';

// 宿主机注入：base 与文件序言对比表
const BASE = ptr(__BASE__);
const entries = __ENTRIES__; // [{name, off, fileBytes: [..first 8 bytes]}]

const hooked = [], clean = [];
for (const e of entries) {
    try {
        const mem = Array.from(new Uint8Array(BASE.add(e.off).readByteArray(8)));
        const same = mem.every((b, i) => b === e.fileBytes[i]);
        (same ? clean : hooked).push(e.name + (same ? '' : ' [mem:' + mem.map(x => x.toString(16)).join(' ') + ']'));
    } catch (err) {
        clean.push(e.name + ' [unreadable]');
    }
}
send({ hooked: hooked, cleanCount: clean.length, clean: clean });
console.log('HOOKED:', hooked.length);
hooked.forEach(h => console.log('  ', h));
console.log('CLEAN:', clean.length);
clean.forEach(h => console.log('  ', h));
