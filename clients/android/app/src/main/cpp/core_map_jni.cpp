#include <jni.h>
#include <string>
#include "core_map.h"

extern "C" JNIEXPORT jstring JNICALL
Java_local_visual_corepose_CoreMap_fromBlaze33(
    JNIEnv *env, jobject /*thiz*/, jfloatArray xyzVis, jint numPeople, jint width, jint height,
    jfloat latencyMs, jstring device) {
    const char *dev = env->GetStringUTFChars(device, nullptr);
    jfloat *buf = nullptr;
    if (xyzVis != nullptr && numPeople > 0) {
        buf = env->GetFloatArrayElements(xyzVis, nullptr);
    }
    char *json = core_map_from_blaze33(buf, numPeople, width, height, latencyMs, dev);
    if (buf != nullptr) {
        env->ReleaseFloatArrayElements(xyzVis, buf, JNI_ABORT);
    }
    env->ReleaseStringUTFChars(device, dev);
    jstring out = env->NewStringUTF(json ? json : "{}");
    core_map_free(json);
    return out;
}
