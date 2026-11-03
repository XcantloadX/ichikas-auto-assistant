extern void __cxa_atexit(void);
int JNI_OnLoad(void *vm, void *r) { (void)vm; (void)r; __cxa_atexit(); return 0x10006; }
