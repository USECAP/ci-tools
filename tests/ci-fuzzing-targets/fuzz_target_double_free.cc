#include <stdlib.h>
#include <stdint.h>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size) {
  char *memory = (char *)malloc(Size);
  free(memory);
  if(Size==2)
      free(memory);
  return 0;
}
