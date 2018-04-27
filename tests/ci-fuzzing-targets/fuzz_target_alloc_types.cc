#include <stdlib.h>
#include <stdint.h>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size) {
  char *memory = new char[Size];
  free(memory);
  return 0;
}
