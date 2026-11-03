'use strict';
const mb = ptr('0x788f219a3000');
// 1) 已知 klass name ptr 读字符串
console.log('str@known-name-ptr(0x788f21d17640):', JSON.stringify(mb.add(0x37640).readCString(24)));
// 2) 20522 的完整 header dump
const b = mb.readByteArray(0x110);
send({ head: Array.from(new Uint8Array(b)).map(x => x.toString(16).padStart(2, '0')).join(' ') });
// 3) 在整个映射范围内找 "GameObject\0"（不限制 28MB）
const found = [];
const size = 0x1C00000; // 29.4MB 稍大于已知
const m = Memory.scanSync(mb, size, '47 61 6d 65 4f 62 6a 65 63 74 00');
for (const h of m) found.push('0x' + h.address.sub(mb).toString(16));
console.log('GameObject offsets in meta mapping:', found.join(', '));
send({ goOffsets: found });
