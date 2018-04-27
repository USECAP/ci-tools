// Toy example from LLVM docs
#include <stdint.h>
#include <stddef.h>

extern "C" {
#include "fuzzme.h"
}

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size) {
  FuzzMe(Data, Size);
  return 0;
}
