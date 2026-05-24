#ifndef LOGGING_H
#define LOGGING_H

#include <android/log.h>
#include <pthread.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define LOG_TAG "REChainMod"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)
#define LOGW(...) __android_log_print(ANDROID_LOG_WARN, LOG_TAG, __VA_ARGS__)
#define LOGD(...) __android_log_print(ANDROID_LOG_DEBUG, LOG_TAG, __VA_ARGS__)

#define BUILD_HASH __DATE__ " " __TIME__

static pthread_mutex_t log_mutex = PTHREAD_MUTEX_INITIALIZER;

static inline void log_locked(int prio, const char *tag, const char *fmt, ...) {
    pthread_mutex_lock(&log_mutex);
    va_list args;
    va_start(args, fmt);
    __android_log_vprint(prio, tag, fmt, args);
    va_end(args);
    pthread_mutex_unlock(&log_mutex);
}

#define LOGI_LOCKED(fmt, ...) log_locked(ANDROID_LOG_INFO, LOG_TAG, fmt, ##__VA_ARGS__)
#define LOGE_LOCKED(fmt, ...) log_locked(ANDROID_LOG_ERROR, LOG_TAG, fmt, ##__VA_ARGS__)
#define LOGW_LOCKED(fmt, ...) log_locked(ANDROID_LOG_WARN, LOG_TAG, fmt, ##__VA_ARGS__)
#define LOGD_LOCKED(fmt, ...) log_locked(ANDROID_LOG_DEBUG, LOG_TAG, fmt, ##__VA_ARGS__)

#define CHECK_NULL(ptr, msg) do { \
    if (!(ptr)) { \
        LOGE("%s: NULL check failed at %s:%d", msg, __FILE__, __LINE__); \
        return; \
    } \
} while (0)

#define CHECK_NULL_VAL(ptr, msg, ret) do { \
    if (!(ptr)) { \
        LOGE("%s: NULL check failed at %s:%d", msg, __FILE__, __LINE__); \
        return (ret); \
    } \
} while (0)

#define ENSURE_NOT_NULL(ptr) do { \
    if (!(ptr)) { \
        LOGE("Unexpected NULL at %s:%d", __FILE__, __LINE__); \
        return; \
    } \
} while (0)

#endif