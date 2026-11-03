#include <jni.h>
#include <android/log.h>
jint JNI_OnLoad(JavaVM *vm, void *r) {
    (void)vm; (void)r;
    __android_log_print(ANDROID_LOG_INFO, "iaa_mini", "MINI LOADED");
    return JNI_VERSION_1_6;
}
