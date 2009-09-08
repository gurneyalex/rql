#include "gecode/support.hh"
#include <stdio.h>

int main() {
#ifndef GECODE_VERSION
    printf("2.1.2\n");
#else
    printf("%s\n", GECODE_VERSION);
#endif
}
