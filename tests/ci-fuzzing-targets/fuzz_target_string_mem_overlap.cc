#include <stdlib.h>
#include <stdint.h>
#include <string.h>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size) {
  char s[] = "Hello everyone.";
  strncpy(s + 4, s, sizeof(s) - 4);
  return 0;
}
