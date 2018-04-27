// Toy example for displaying a timeout error
#include <stdint.h>
#include <stddef.h>

size_t do_smth(const uint8_t *Data, size_t Size) {
  volatile int counter = 0;
  if (Size > 10) {
    while(1) {
      if (counter == 1) return Size;
    }
  }
  return 0;
}

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size) {
  size_t ret = do_smth(Data, Size);
  return 0;
}
