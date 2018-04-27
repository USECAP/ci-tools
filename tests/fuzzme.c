//
// Created by user on 2/22/18.
//
#include "fuzzme.h"

int hello(const uint8_t *data, size_t size) {
    if (size > 0 && data[0] == 'H')
        if (size > 1 && data[1] == 'I')
            if (size > 2 && data[2] == '!')
                __builtin_trap();
    return 0;
}

int FuzzMe(const uint8_t *Data, size_t DataSize) {
    return DataSize >= 3 &&
           Data[0] == 'F' &&
           Data[1] == 'U' &&
           Data[2] == 'Z' &&
           Data[3] == 'Z';  // :‑<
}
