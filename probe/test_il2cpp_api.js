// 实验 15：无分配 API 全链验证 + GC 堆扫描 GameObject 实例 + 字段读取
'use strict';

const trampCache = {};
const itf = Module.getExportByName('libhoudini.so', 'NativeBridgeItf');
const pGetTrampoline = itf.add(24).readPointer();
const getTrampolineFn = new NativeFunction(pGetTrampoline, 'pointer', ['pointer', 'pointer', 'pointer', 'uint32', 'uint32']);

function tramp(name, shorty) {
    const key = name + '|' + shorty;
    if (trampCache[key]) return trampCache[key];
    const t = getTrampolineFn(ptr(0), Memory.allocUtf8String(name), Memory.allocUtf8String(shorty), shorty.length, 0);
    if (t.isNull()) throw new Error('no trampoline for ' + name);
    trampCache[key] = t;
    return t;
}
function nf(name, shorty, ret, args) { return new NativeFunction(tramp(name, shorty), ret, args); }
function readCStr(p) { return p.isNull() ? null : p.readCString(); }

const domainGet = nf('il2cpp_domain_get', 'L', 'pointer', []);
const domainGetAssemblies = nf('il2cpp_domain_get_assemblies', 'LL', 'pointer', ['pointer', 'pointer']);
const assemblyGetImage = nf('il2cpp_assembly_get_image', 'LL', 'pointer', ['pointer']);
const imageGetName = nf('il2cpp_image_get_name', 'LL', 'pointer', ['pointer']);
const classFromName = nf('il2cpp_class_from_name', 'LLL', 'pointer', ['pointer', 'pointer', 'pointer']);
const classGetName = nf('il2cpp_class_get_name', 'LL', 'pointer', ['pointer']);
const classGetField = nf('il2cpp_class_get_field_from_name', 'LLL', 'pointer', ['pointer', 'pointer']);
const fieldGetOffset = nf('il2cpp_field_get_offset', 'LL', 'int', ['pointer']);
const fieldGetName = nf('il2cpp_field_get_name', 'LL', 'pointer', ['pointer']);
const fieldGetValueObject = nf('il2cpp_field_get_value_object', 'LLL', 'pointer', ['pointer', 'pointer']);
const fieldGetClass = nf('il2cpp_field_get_parent', 'LL', 'pointer', ['pointer']);
const classIsValueType = nf('il2cpp_class_is_valuetype', 'LI', 'int', ['pointer']);
const stringChars = nf('il2cpp_string_chars', 'LL', 'pointer', ['pointer']);
const classInstanceSize = nf('il2cpp_class_instance_size', 'LI', 'int', ['pointer']);

const domain = domainGet();
console.log('domain =', domain);
const sizeBuf = Memory.alloc(8);
const assemblies = domainGetAssemblies(domain, sizeBuf);
const count = sizeBuf.readULong().toNumber();
console.log('assemblies =', count);

let coreImage = null;
for (let i = 0; i < count; i++) {
    const asm = assemblies.add(i * Process.pointerSize).readPointer();
    const img = assemblyGetImage(asm);
    const nm = readCStr(imageGetName(img));
    if (nm === 'UnityEngine.CoreModule.dll') { coreImage = img; break; }
}
console.log('coreImage =', coreImage);
if (!coreImage) throw new Error('CoreModule not found');

const goClass = classFromName(coreImage, Memory.allocUtf8String('UnityEngine'), Memory.allocUtf8String('GameObject'));
console.log('GameObject klass =', goClass, 'name =', readCStr(classGetName(goClass)), 'instance size =', classInstanceSize(goClass));

// GameObject 的字段与偏移
const fieldNames = ['m_CachedPtr', 'm_ComponentList', 'm_CanvasRenderer', 'm_Canvas', 'm_TagString', 'm_IsActive', 'm_Name'];
const fields = {};
for (const fn of fieldNames) {
    try {
        const f = classGetField(goClass, Memory.allocUtf8String(fn));
        if (f.isNull()) { console.log('field', fn, ': NOT FOUND'); continue; }
        const off = fieldGetOffset(f);
        fields[fn] = { field: f, offset: off };
        console.log('field', fn, 'offset =', off);
    } catch (e) { console.log('field', fn, 'ERR', e); }
}
send({ goClass: String(goClass), fields: fields });

// GC 堆扫描：找 klass == goClass 的对象
// Il2CppObject: [klass*][monitor*][fields...]
const klassPattern = goClass.toString(16).replace(/^0x/, '').padStart(16, '0').match(/../g).reverse().join(' ');
console.log('scan pattern:', klassPattern);
const ranges = Process.enumerateRangesSync('rw-');
let instances = [];
let total = 0;
for (const r of ranges) {
    if (r.size > 512 * 1024 * 1024) continue;
    total += r.size;
    try {
        const m = Memory.scanSync(r.base, r.size, klassPattern);
        for (const hit of m) {
            // 简单校验：monitor 字段（+8）通常为 0 或堆指针；且实例大小范围内可读
            try {
                const mon = hit.address.add(8).readPointer();
                const nameObj = hit.address.add(fields['m_Name'].offset).readPointer();
                if (nameObj.isNull()) continue;
                // 名字对象也应有合法 klass（System.String）
                const s = readCStr(stringChars(nameObj));
                if (s !== null && s.length < 256) {
                    instances.push({ obj: String(hit.address), name: s, monitor: String(mon) });
                }
            } catch (e) { }
        }
    } catch (e) { }
    if (instances.length > 500) break;
}
console.log('scanned', (total / 1048576).toFixed(0), 'MB rw, found', instances.length, 'GameObject instances');
console.log(instances.slice(0, 30).map(x => x.name).join(' | '));
send({ count: instances.length, samples: instances.slice(0, 50) });
