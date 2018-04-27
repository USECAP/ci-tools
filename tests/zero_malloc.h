#include <inttypes.h>
#include <stdlib.h>
#include <string.h>

typedef void stream_t;
typedef uint64_t UUID_t;

typedef struct {
  char *psz_text;
} MP4_Box_data_string_t;

typedef struct {
  MP4_Box_data_string_t *p_string;
} MP4_Box_data_t;

typedef struct MP4_Box_s MP4_Box_t;

/* the most basic structure */
struct MP4_Box_s {
  off_t i_pos;      /* absolute position */

  uint32_t i_type;
  uint32_t i_shortsize;
  uint32_t i_handler;  /**/
  uint32_t i_index;    /* indexed list (ilst) */

  enum {
    BOX_FLAG_NONE = 0,
    BOX_FLAG_INCOMPLETE,
  } e_flags;

  UUID_t i_uuid;  /* Set if i_type == "uuid" */

  uint64_t i_size; /* always set so use it */

  MP4_Box_t *p_father; /* pointer on the father Box */
  MP4_Box_t *p_first;  /* pointer on the first child Box */
  MP4_Box_t *p_last;
  MP4_Box_t *p_next;   /* pointer on the next boxes at the same level */

  void (*pf_free)(MP4_Box_t *p_box); /* pointer to free function for this box */

  MP4_Box_data_t data;   /* union of pointers on extended data depending
                                on i_type (or i_usertype) */
};

extern int MP4_ReadBox_String(stream_t *p_stream, MP4_Box_t *p_box);
