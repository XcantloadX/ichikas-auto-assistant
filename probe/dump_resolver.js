'use strict';
// dump resolver（gateway 调用的 0x788f49c8ccd0）周边更大范围
const g = ptr('0x788f49c8ccd0');
const dump = g.sub(0x200).readByteArray(0x800);
send({ bytes: Array.from(new Uint8Array(dump)).map(x => x.toString(16).padStart(2, '0')).join(' ') });
