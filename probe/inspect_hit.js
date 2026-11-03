'use strict';
const h = ptr('0x788f00258fd8');
const words = [];
for (let k = -0x30; k <= 0x30; k += 8) {
    try {
        const v = h.add(k).readPointer();
        let s = null;
        try { s = v.readCString(30); } catch (e) { }
        words.push((k >= 0 ? '+' : '') + k + ': ' + v + (s && /^[-~ ]{2,30}$/.test(s) ? ' (\'' + s.slice(0, 20) + '\')' : ''));
    } catch (e) { words.push((k >= 0 ? '+' : '') + k + ': ?'); }
}
console.log(words.join(' | '));
send({ words: words });
