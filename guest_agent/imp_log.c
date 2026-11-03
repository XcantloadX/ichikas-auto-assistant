#include <android/log.h>
int JNI_OnLoad(void *vm, void *r) { (void)vm; (void)r; __android_log_print(4, "t", "x"); return 0x10006; }
