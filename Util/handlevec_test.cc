#include "Util/handlevec.h"
#include "Util/assert.h"
#include "Util/handle.h"

#include <iostream>

using namespace std;

namespace cwerg {

ostream& operator<<(ostream& os, const Handle& h) {
  os << h.index() << "::" << int(h.raw_kind());
  return os;
}

void Test() {
  HandleVec hv1 = HandleVec::New(256);
  HandleVec hv2 = HandleVec::New(256);
  HandleVec hv3 = HandleVec::New(256);

  ASSERT(hv1.Equal(hv2), "");

  for (int i = 0; i < 256; ++i) {
    hv1.Set(i, Handle(i, 11));
  }
  for (int i = 0; i < 256; ++i) {
    hv2.Set(i, Handle(i, 22));
  }
  for (int i = 0; i < 256; ++i) {
    ASSERT(hv1.Get(i) == Handle(i, 11), "");
  }
  for (int i = 0; i < 256; ++i) {
    ASSERT(hv2.Get(i) == Handle(i, 22), "");
  }

  hv3.CopyFrom(hv2);
  for (int i = 0; i < 256; ++i) {
    ASSERT(hv3.Get(i) == Handle(i, 22), "");
  }
  hv3.ClearWith(Handle(1, 33));
  for (int i = 0; i < 256; ++i) {
    ASSERT(hv3.Get(i) == Handle(1, 33), "");
  }
}

}  // namespace cwerg

int main() {
  cwerg::Test();
  return 0;
}
