'use strict';
send({ t1: typeof '788f30d0b000', v: '788f30d0b000' });
try {
    const p = ptr('788f30d0b000');
    send({ literalPtrOk: String(p) });
} catch (e) {
    send({ literalPtrErr: String(e) });
}
try {
    const p2 = ptr(baseStr);
    send({ varPtrOk: String(p2) });
} catch (e) {
    send({ varPtrErr: String(e) });
}
try {
    const p3 = new NativePointer(baseStr);
    send({ ctorOk: String(p3) });
} catch (e) {
    send({ ctorErr: String(e) });
}
