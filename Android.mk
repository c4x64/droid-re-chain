LOCAL_PATH := $(call my-dir)
include $(CLEAR_VARS)
LOCAL_MODULE := mod
LOCAL_SRC_FILES := src/main.cpp
LOCAL_SRC_FILES := src/main.cpp
LOCAL_C_INCLUDES := $(LOCAL_PATH)/include
LOCAL_CFLAGS := -Wall -Wextra -O2 -fvisibility=hidden -fPIC
LOCAL_LDFLAGS := -llog -ldl
LOCAL_LDLIB := -llog -ldl
LOCAL_LDLIBS := -llog -ldl
LOCAL_ARM_MODE := arm64
include $(BUILD_SHARED_LIBRARY)