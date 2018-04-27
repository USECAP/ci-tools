#include <stdlib.h>
#include <stdint.h>
#include <string.h>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size) {
  char s[] = "Hello everyone.";
  char g[sizeof(s)];
  strncpy(g, s, -10);
  return 0;
}
