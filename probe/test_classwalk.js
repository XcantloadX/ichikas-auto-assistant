// 实验 28：类表行走 + Transform 实例扫描 + 原生结构统计
'use strict';

const META_BASE = ptr(__META_BASE__);
const META_SIZE = __META_SIZE__;
const GO_KLASS = ptr(__GO_KLASS__);

function inMeta(p) { return p.compare(META_BASE) >= 0 && p.compare(META_BASE.add(META_SIZE)) < 0; }

function klassInfo(k) {
    try {
        const namePtr = k.add(0x10).readPointer();
        const nsPtr = k.add(0x18).readPointer();
        if (!inMeta(namePtr) || !inMeta(nsPtr)) return null;
        const name = namePtr.readCString(48);
        const ns = nsPtr.readCString(48);
        if (!name || !ns) return null;
        // name 必须在 48 字节内结束（避免读到下一个名字）
        if (name.indexOf('\u0000') === -1) return null;  // readCString 已按 null 截断；多余检查无妨
        return { name: name, ns: ns };
    } catch (e) { return null; }
}

// 1) 类表行走：从 GameObject 出发双向走，收集感兴趣类
const want = ['Transform', 'RectTransform', 'Canvas', 'TextMeshProUGUI', 'TMP_Text', 'Selectable', 'Button', 'CanvasGroup', 'CanvasRenderer', 'Object'];
const found = {}; // name -> klass
let cursor = GO_KLASS;
let walked = 0;
// 向后走 4096 个（0x180 步），向前 512
for (let i = 0; i < 4096; i++) {
    const k = GO_KLASS.add(i * 0x180);
    const info = klassInfo(k);
    if (info && want.indexOf(info.name) !== -1 && !found[info.name]) {
        found[info.name] = String(k);
        if (info.ns === 'UnityEngine' || info.ns === 'UnityEngine.UI' || info.ns === 'TMPro') {
            // 区分同名：以 ns 为准记录
            found[info.ns + '.' + info.name] = String(k);
        }
    }
}
for (let i = 1; i <= 512; i++) {
    const k = GO_KLASS.sub(i * 0x180);
    const info = klassInfo(k);
    if (info && want.indexOf(info.name) !== -1 && !found[info.name]) {
        found[info.name] = String(k);
        found[info.ns + '.' + info.name] = String(k);
    }
}
console.log('walk results:', JSON.stringify(found, null, 1));
send({ found: found });
