'use strict';
// dump lookup+0x26c 周边代码（找登记函数）
const lookup = ptr('__LOOKUP__');
const dump = lookup.readByteArray(0x400);
send({ bytes: Array.from(new Uint8Array(dump)).map(x => x.toString(16).padStart(2, '0')).join(' ') });
