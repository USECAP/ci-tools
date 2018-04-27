// Toy example for displaying a leak error
#include <stdlib.h>
#include <stdint.h>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size) {
  char *memory = (char *)malloc(Size);
  return 0;
}
