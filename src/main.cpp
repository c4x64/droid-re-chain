#define _GNU_SOURCE
#include <dlfcn.h>
#include <jni.h>
#include <android/log.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/mman.h>
#include "il2cpp.h"

#define LOG_TAG "REChainMod"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)
#define LOGW(...) __android_log_print(ANDROID_LOG_WARN, LOG_TAG, __VA_ARGS__)

#define MAX_HOOKS 64

static struct {
    Il2CppMethodPointer original;
    Il2CppMethodPointer hook;
} hooks[MAX_HOOKS];

static int hook_count = 0;

static void scan_class_methods(Il2CppClass *klass) {
    if (!klass) return;
    void *iter = NULL;
    MethodInfo const *method;
    while ((method = il2cpp.class_get_methods(klass, &iter)) != NULL) {
        const char *mname = il2cpp.method_get_name(method);
        Il2CppMethodPointer ptr = il2cpp.method_get_pointer(method);
        LOGI("  [method] %s -> %p", mname, (void *)ptr);
    }
}

static void dump_assembly_summary(void) {
    size_t count = 0;
    Il2CppAssembly **assemblies = il2cpp.get_assemblies(&count);
    if (!assemblies) {
        LOGE("get_assemblies returned NULL");
        return;
    }
    LOGI("=== Assembly Dump (%zu assemblies) ===", count);
    for (size_t i = 0; i < count; i++) {
        Il2CppImage *image = il2cpp.get_image_from_assembly(assemblies[i]);
        if (!image) continue;
        LOGI("[%zu] %s (%u types)", i, image->name, image->typeCount);
    }
}

static void dump_assembly_methods(const char *name_filter) {
    size_t count = 0;
    Il2CppAssembly **assemblies = il2cpp.get_assemblies(&count);
    if (!assemblies) return;
    for (size_t i = 0; i < count; i++) {
        Il2CppImage *image = il2cpp.get_image_from_assembly(assemblies[i]);
        if (!image) continue;
        if (name_filter && strcmp(image->name, name_filter) != 0) continue;
        LOGI("--- Assembly: %s ---", image->name);
        uint32_t max = image->typeCount < 200 ? image->typeCount : 200;
        for (uint32_t t = 0; t < max; t++) {
            Il2CppClass *klass = image->types[t];
            if (!klass) continue;
            scan_class_methods(klass);
        }
    }
}

__attribute__((constructor))
static void mod_init(void) {
    LOGI("===== REChain Mod Loaded =====");

    void *handle = dlopen("libil2cpp.so", RTLD_LAZY | RTLD_NOLOAD);
    if (!handle) {
        handle = dlopen("libil2cpp.so", RTLD_LAZY | RTLD_LOCAL);
    }
    if (!handle) {
        LOGE("dlopen libil2cpp.so failed: %s", dlerror());
        return;
    }
    dlclose(handle);

    if (il2cpp_init("libil2cpp.so") != 0) {
        LOGE("il2cpp_init failed");
        return;
    }
    LOGI("il2cpp runtime initialized");

    dump_assembly_summary();
    LOGI("===== REChain Mod Init Complete =====");
}