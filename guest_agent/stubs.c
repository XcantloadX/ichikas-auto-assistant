/* MuMu 的 arm64 guest libc 缺失符号的空桩（我们不用 atexit 机制） */
void __cxa_atexit(void *f, void *o, void *d) { (void)f; (void)o; (void)d; }
void __cxa_finalize(void *d) { (void)d; }
void __register_atfork(void *a, void *b, void *c, void *d) { (void)a; (void)b; (void)c; (void)d; }
