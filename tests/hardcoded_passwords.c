/* Taken from
 * https://ftp.gnu.org/old-gnu/Manuals/glibc-2.2.3/html_chapter/libc_32.html */

/* Test cases for HardcodedPasswords */

#include <crypt.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(void) {
  /* Hashed form of "GNU libc manual". */
  const char* const pass = "$1$/iSaq7rB$EoUw5jJPPvAPECNaaWzMK/";

  char* result;
  int ok;

  /* Read in the user's password and encrypt it,
     passing the expected password in as the salt. */
  result = crypt(getpass("Password:"), pass);

  /* Test the result. */
  ok = strcmp(result, pass) == 0;

  puts(ok ? "Access granted." : "Access denied.");
  return ok ? 0 : 1;
}