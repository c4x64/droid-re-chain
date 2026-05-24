#ifndef IL2CPP_H
#define IL2CPP_H

#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <errno.h>

#define IL2CPP_CALL __attribute__((pcs("aapcs64")))
#define IL2CPP_EXPORT __attribute__((visibility("default")))

typedef uint32_t Il2CppMethodSlot;
typedef uintptr_t Il2CppMethodPointer;

typedef struct Il2CppClass Il2CppClass;
typedef struct Il2CppObject {
    Il2CppClass *klass;
    void *monitor;
} Il2CppObject;

typedef struct Il2CppImage {
    const char *name;
    void *assembly;
    uint32_t typeCount;
    Il2CppClass **types;
} Il2CppImage;

typedef struct Il2CppAssembly {
    Il2CppImage *image;
    void *token;
    uint32_t refCount;
} Il2CppAssembly;

typedef struct MethodInfo {
    Il2CppMethodPointer methodPtr;
    Il2CppMethodSlot slot;
    Il2CppClass *klass;
    const char *name;
    const char *returnType;
    uint8_t parametersCount;
} MethodInfo;

typedef void *(*il2cpp_resolve_icall_fn)(const char *name);
typedef Il2CppAssembly **(*il2cpp_get_assemblies_fn)(size_t *size);
typedef Il2CppClass *(*il2cpp_class_from_name_fn)(Il2CppImage *image, const char *ns, const char *name);
typedef Il2CppImage *(*il2cpp_get_image_from_assembly_fn)(const Il2CppAssembly *assembly);
typedef MethodInfo const *(*il2cpp_class_get_methods_fn)(Il2CppClass *klass, void **iter);
typedef const char *(*il2cpp_method_get_name_fn)(const MethodInfo *method);
typedef Il2CppMethodPointer (*il2cpp_method_get_pointer_fn)(const MethodInfo *method);
typedef Il2CppClass *(*il2cpp_object_get_class_fn)(Il2CppObject *obj);
typedef Il2CppClass *(*il2cpp_class_from_system_type_fn)(void *type);
typedef void *(*il2cpp_object_new_fn)(Il2CppClass *klass);
typedef Il2CppClass *(*il2cpp_class_get_nested_types_fn)(Il2CppClass *klass, void **iter);

static struct {
    void *handle;
    il2cpp_resolve_icall_fn resolve_icall;
    il2cpp_get_assemblies_fn get_assemblies;
    il2cpp_class_from_name_fn class_from_name;
    il2cpp_get_image_from_assembly_fn get_image_from_assembly;
    il2cpp_class_get_methods_fn class_get_methods;
    il2cpp_method_get_name_fn method_get_name;
    il2cpp_method_get_pointer_fn method_get_pointer;
    il2cpp_object_get_class_fn object_get_class;
    il2cpp_class_from_system_type_fn class_from_system_type;
    il2cpp_object_new_fn object_new;
    il2cpp_class_get_nested_types_fn class_get_nested_types;
} il2cpp;

static int il2cpp_init(const char *libpath) {
    il2cpp.handle = dlopen(libpath, RTLD_LAZY | RTLD_NOLOAD);
    if (!il2cpp.handle) {
        il2cpp.handle = dlopen(libpath, RTLD_LAZY | RTLD_LOCAL);
    }
    if (!il2cpp.handle) return -1;

    il2cpp.resolve_icall = (il2cpp_resolve_icall_fn)dlsym(il2cpp.handle, "il2cpp_resolve_icall");
    il2cpp.get_assemblies = (il2cpp_get_assemblies_fn)dlsym(il2cpp.handle, "il2cpp_get_assemblies");
    il2cpp.class_from_name = (il2cpp_class_from_name_fn)dlsym(il2cpp.handle, "il2cpp_class_from_name");
    il2cpp.get_image_from_assembly = (il2cpp_get_image_from_assembly_fn)dlsym(il2cpp.handle, "il2cpp_get_image_from_assembly");
    il2cpp.class_get_methods = (il2cpp_class_get_methods_fn)dlsym(il2cpp.handle, "il2cpp_class_get_methods");
    il2cpp.method_get_name = (il2cpp_method_get_name_fn)dlsym(il2cpp.handle, "il2cpp_method_get_name");
    il2cpp.method_get_pointer = (il2cpp_method_get_pointer_fn)dlsym(il2cpp.handle, "il2cpp_method_get_pointer");
    il2cpp.object_get_class = (il2cpp_object_get_class_fn)dlsym(il2cpp.handle, "il2cpp_object_get_class");
    il2cpp.class_from_system_type = (il2cpp_class_from_system_type_fn)dlsym(il2cpp.handle, "il2cpp_class_from_system_type");
    il2cpp.object_new = (il2cpp_object_new_fn)dlsym(il2cpp.handle, "il2cpp_object_new");
    il2cpp.class_get_nested_types = (il2cpp_class_get_nested_types_fn)dlsym(il2cpp.handle, "il2cpp_class_get_nested_types");
    return 0;
}

static Il2CppClass *il2cpp_find_class(const char *assembly_name, const char *ns, const char *name) {
    size_t count = 0;
    Il2CppAssembly **assemblies = il2cpp.get_assemblies(&count);
    if (!assemblies) return NULL;
    for (size_t i = 0; i < count; ++i) {
        Il2CppImage *image = il2cpp.get_image_from_assembly(assemblies[i]);
        if (!image) continue;
        if (assembly_name && strcmp(image->name, assembly_name) != 0) continue;
        Il2CppClass *klass = il2cpp.class_from_name(image, ns, name);
        if (klass) return klass;
    }
    return NULL;
}

static MethodInfo const *il2cpp_find_method(Il2CppClass *klass, const char *method_name) {
    if (!klass) return NULL;
    void *iter = NULL;
    MethodInfo const *method;
    while ((method = il2cpp.class_get_methods(klass, &iter)) != NULL) {
        const char *mname = il2cpp.method_get_name(method);
        if (mname && strcmp(mname, method_name) == 0) {
            return method;
        }
    }
    return NULL;
}

#endif