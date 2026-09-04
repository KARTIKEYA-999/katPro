CC ?= clang
CFLAGS ?= -O3 -Wall -Wextra -fPIC
UNAME_S := $(shell uname -s)

ifeq ($(UNAME_S),Darwin)
    TARGET = libcqueue.dylib
    LDFLAGS = -dynamiclib
else
    TARGET = libcqueue.so
    LDFLAGS = -shared
endif

all: $(TARGET)

$(TARGET): queue_fast.o
	$(CC) $(LDFLAGS) -o $@ $^

queue_fast.o: queue_fast.c queue_fast.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f *.o $(TARGET) libcqueue.dylib libcqueue.so

.PHONY: all clean
