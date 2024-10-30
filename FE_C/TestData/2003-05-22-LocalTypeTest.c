#include "std_lib.h"   // needed because printf may be rewritten to call helpers defined here

int printf( const char *restrict format, ... );


struct sometimes {
  short offset; short bit;
  short live_length; short calls_crossed;
} Y;

int main() {
  int X;
  {
    struct sometimes { int X,  Y; } S;
    S.X = 1;
    X = S.X;
  }
  { 
    struct sometimes { signed char X; } S;
    S.X = -1;
    X += S.X;
  }
  X += Y.offset;

  printf("Result is %d\n", X);
  return X;
}
