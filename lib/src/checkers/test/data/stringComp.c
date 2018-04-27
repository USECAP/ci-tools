#include <string.h>
#include <stdio.h>

#define STATIC_STRING "DEFINE_STATIC_STRING"

typedef struct staticStings {
    char buf1[100];
    char buf2[250];
} sString;

int compare(char *input) {
  if (strcmp(input, "hello world") == 0) {
    return 1;
  } else {
    return 0;
  }
}

//some string and byte functions
void examleMemFunctions(){
  char buffer[100];
  memcpy(buffer,STATIC_STRING,strlen(STATIC_STRING));
  memmove(buffer,STATIC_STRING,strlen(STATIC_STRING));
  memcmp(buffer,STATIC_STRING,strlen(STATIC_STRING));
  strcat(buffer,"STATIC STRING");
  strncat(buffer,STATIC_STRING,strlen(STATIC_STRING));
  strcmp(buffer,"STATIC STRING");
  strncmp(buffer,STATIC_STRING,strlen(STATIC_STRING));
  strcoll(buffer,"STATIC STRING");
  strcpy(buffer,"STATIC STRING");
  strncpy(buffer,STATIC_STRING,strlen(STATIC_STRING));
  strxfrm(buffer,STATIC_STRING,strlen(STATIC_STRING));
  return;
}

int main(int argc, char **argv) {
  examleMemFunctions();
  return 0;
}