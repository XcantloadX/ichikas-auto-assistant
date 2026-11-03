extern void __register_atfork(void);
int JNI_OnLoad(void *vm, void *r) { (void)vm; (void)r; __register_atfork(); return 0x10006; }
