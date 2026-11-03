// 最终版 klass 定位：全内存字符串实例 + 分块指针交叉验证（异步分片避免超时）
'use strict';

const state = {
    goAddrs: [], unAddrs: [],
    ranges: [], rangeIdx: 0,
    klasses: [],
};

function step1() {
    // 收集 rw 内存中的字符串实例
    const ranges = Process.enumerateRangesSync('rw-').filter(r => !r.file && r.size >= 0x4000 && r.size <= 512 * 1024 * 1024);
    state.ranges = ranges;
    console.log('ranges:', ranges.length, 'total MB:', (ranges.reduce((a, r) => a + r.size, 0) / 1048576).toFixed(0));
    for (const r of ranges) {
        try {
            for (const h of Memory.scanSync(r.base, r.size, '47 61 6d 65 4f 62 6a 65 63 74 00')) state.goAddrs.push(h.address);
            for (const h of Memory.scanSync(r.base, r.size, '55 6e 69 74 79 45 6e 67 69 6e 65 00')) state.unAddrs.push(h.address);
        } catch (e) { }
    }
    console.log('go instances:', state.goAddrs.length, 'un instances:', state.unAddrs.length);
    send({ goN: state.goAddrs.length, unN: state.unAddrs.length });
    step2Chunk();
}

function step2Chunk() {
    // 对每个 un 实例，扫指针；分片处理避免阻塞
    const t0 = Date.now();
    while (state.rangeIdx < state.ranges.length && Date.now() - t0 < 4000) {
        const r = state.ranges[state.rangeIdx];
        for (const ua of state.unAddrs) {
            const hex = String(ua).slice(2).padStart(16, '0');
            const pat = hex.match(/../g).reverse().join(' ');
            let hits = [];
            try { hits = Memory.scanSync(r.base, r.size, pat); } catch (e) { continue; }
            for (const h of hits) {
                try {
                    const namePtr = h.sub(8).readPointer();
                    for (const ga of state.goAddrs) {
                        if (ga.equals(namePtr)) {
                            state.klasses.push(String(h.sub(0x18)));
                            break;
                        }
                    }
                } catch (e) { }
            }
        }
        state.rangeIdx++;
    }
    if (state.rangeIdx < state.ranges.length) {
        setTimeout(step2Chunk, 0);
    } else {
        console.log('klasses found:', state.klasses.length);
        state.klasses.slice(0, 10).forEach(k => console.log('  ', k));
        send({ klasses: state.klasses, done: true });
    }
}

step1();
