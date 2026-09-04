CXX ?= clang++
UNAME_S := $(shell uname -s)

ifeq ($(UNAME_S),Darwin)
    SDK_PATH := $(shell xcrun --show-sdk-path 2>/dev/null || echo /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk)
    CXXFLAGS ?= -O3 -Wall -Wextra -std=c++17 -fPIC -isysroot $(SDK_PATH) -I$(SDK_PATH)/usr/include/c++/v1
    TARGET = libcppqueue_opt.dylib
    LDFLAGS = -dynamiclib
else
    CXXFLAGS ?= -O3 -Wall -Wextra -std=c++17 -fPIC
    TARGET = libcppqueue_opt.so
    LDFLAGS = -shared
endif

all: $(TARGET)

$(TARGET): optimizer.o
	$(CXX) $(LDFLAGS) -o $@ $^

optimizer.o: optimizer.cpp optimizer.h
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f *.o $(TARGET) libcppqueue_opt.dylib libcppqueue_opt.so

.PHONY: all clean
