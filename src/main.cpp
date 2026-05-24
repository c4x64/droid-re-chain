#define _GNU_SOURCE
#include <dlfcn.h>
#include <jni.h>
#include <android/log.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/mman.h>
#include <pthread.h>
#include "il2cpp.h"
#include "logging.h"

#define MAX_HOOKS 64
#define MOD_VERSION "1.0.0"
#define CONSTRUCTOR_MAGIC 0x52454348

static struct {
    Il2CppMethodPointer original;
    Il2CppMethodPointer hook;
    char name[128];
    int active;
} hooks[MAX_HOOKS];

static int hook_count = 0;
static pthread_mutex_t hooks_mutex = PTHREAD_MUTEX_INITIALIZER;
static int constructor_guard = 0;
static int mod_initialized = 0;

static void scan_class_methods(Il2CppClass *klass) {
    CHECK_NULL(klass, "scan_class_methods klass");
    void *iter = NULL;
    MethodInfo const *method;
    while ((method = il2cpp.class_get_methods(klass, &iter)) != NULL) {
        const char *mname = il2cpp.method_get_name(method);
        if (!mname) continue;
        Il2CppMethodPointer ptr = il2cpp.method_get_pointer(method);
        LOGI("  [method] %s -> %p", mname, (void *)ptr);
    }
}

static void dump_assembly_summary(void) {
    size_t count = 0;
    Il2CppAssembly **assemblies = il2cpp.get_assemblies(&count);
    CHECK_NULL(assemblies, "dump_assembly_summary assemblies");
    LOGI("=== Assembly Dump (%zu assemblies) | Build: %s | v%s ===", count, BUILD_HASH, MOD_VERSION);
    for (size_t i = 0; i < count; i++) {
        Il2CppImage *image = NULL;
        if (assemblies[i]) {
            image = il2cpp.get_image_from_assembly(assemblies[i]);
        }
        if (!image) continue;
        LOGI("[%zu] %s (%u types)", i, image->name ? image->name : "?", image->typeCount);
    }
}

static void dump_assembly_methods(const char *name_filter) {
    size_t count = 0;
    Il2CppAssembly **assemblies = il2cpp.get_assemblies(&count);
    CHECK_NULL(assemblies, "dump_assembly_methods assemblies");
    for (size_t i = 0; i < count; i++) {
        Il2CppImage *image = NULL;
        if (assemblies[i]) {
            image = il2cpp.get_image_from_assembly(assemblies[i]);
        }
        if (!image || !image->name) continue;
        if (name_filter && strcmp(image->name, name_filter) != 0) continue;
        LOGI("--- Assembly: %s ---", image->name);
        uint32_t max = image->typeCount < 200 ? image->typeCount : 200;
        for (uint32_t t = 0; t < max; t++) {
            Il2CppClass *klass = image->types ? image->types[t] : NULL;
            if (!klass) continue;
            scan_class_methods(klass);
        }
    }
}

int install_hook(const char *method_name, Il2CppMethodPointer hook_fn) {
    pthread_mutex_lock(&hooks_mutex);
    if (hook_count >= MAX_HOOKS) {
        pthread_mutex_unlock(&hooks_mutex);
        LOGE("hook limit reached (%d)", MAX_HOOKS);
        return -1;
    }
    size_t count = 0;
    Il2CppAssembly **assemblies = il2cpp.get_assemblies(&count);
    if (!assemblies) {
        pthread_mutex_unlock(&hooks_mutex);
        return -1;
    }
    for (size_t i = 0; i < count && hook_count < MAX_HOOKS; i++) {
        Il2CppImage *image = assemblies[i] ? il2cpp.get_image_from_assembly(assemblies[i]) : NULL;
        if (!image) continue;
        uint32_t max = image->typeCount < 200 ? image->typeCount : 200;
        for (uint32_t t = 0; t < max && image->types; t++) {
            Il2CppClass *klass = image->types[t];
            if (!klass) continue;
            void *iter = NULL;
            MethodInfo const *method;
            while ((method = il2cpp.class_get_methods(klass, &iter)) != NULL) {
                const char *mname = il2cpp.method_get_name(method);
                if (mname && strcmp(mname, method_name) == 0) {
                    hooks[hook_count].original = il2cpp.method_get_pointer(method);
                    hooks[hook_count].hook = hook_fn;
                    strncpy(hooks[hook_count].name, method_name, sizeof(hooks[hook_count].name) - 1);
                    hooks[hook_count].active = 1;
                    hook_count++;
                    pthread_mutex_unlock(&hooks_mutex);
                    LOGI("Hook installed: %s -> %p", method_name, (void *)hook_fn);
                    return 0;
                }
            }
        }
    }
    pthread_mutex_unlock(&hooks_mutex);
    LOGE("Hook failed: method '%s' not found", method_name);
    return -1;
}

__attribute__((constructor))
static void mod_init(void) {
    if (__sync_lock_test_and_set(&constructor_guard, CONSTRUCTOR_MAGIC)) {
        LOGW("mod_init already called, skipping re-init");
        return;
    }
    LOGI("===== REChain Mod v%s Loaded | Build: %s =====", MOD_VERSION, BUILD_HASH);
    void *handle = dlopen("libil2cpp.so", RTLD_LAZY | RTLD_NOLOAD);
    if (!handle) {
        handle = dlopen("libil2cpp.so", RTLD_LAZY | RTLD_LOCAL);
    }
    if (!handle) {
        LOGE("dlopen libil2cpp.so failed: %s", dlerror());
        __sync_lock_release(&constructor_guard);
        return;
    }
    dlclose(handle);
    if (il2cpp_init("libil2cpp.so") != 0) {
        LOGE("il2cpp_init failed");
        __sync_lock_release(&constructor_guard);
        return;
    }
    LOGI("il2cpp runtime initialized");
    dump_assembly_summary();
    mod_initialized = 1;
    LOGI("===== REChain Mod Init Complete =====");
    __sync_lock_release(&constructor_guard);
}

__attribute__((destructor))
static void mod_fini(void) {
    LOGI("REChain Mod unloading, %d hooks active", hook_count);
    pthread_mutex_lock(&hooks_mutex);
    for (int i = 0; i < hook_count; i++) {
        hooks[i].active = 0;
    }
    pthread_mutex_unlock(&hooks_mutex);
    LOGI("REChain Mod unloaded");
}