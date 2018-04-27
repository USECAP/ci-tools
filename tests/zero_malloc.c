#include "zero_malloc.h"

extern int MP4_ReadBox_String(stream_t *p_stream, MP4_Box_t *p_box) {
  uint8_t *p_peek = malloc(p_box->i_size);

  p_box->data.p_string->psz_text =
      malloc(p_box->i_size - 8 - 1); /* +\0, -name, -size */
  if (p_box->data.p_string->psz_text == NULL)
    return 0;

  memcpy(p_box->data.p_string->psz_text, p_peek, p_box->i_size - 8);
  p_box->data.p_string->psz_text[p_box->i_size - 8] = '\0';

  return 0;
}
