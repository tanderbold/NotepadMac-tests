/* Exports the interface but offers no command: the host must skip it. */
#include "NotepadMacPlugin.h"
void nppmac_setInfo(NppMacData data) { (void)data; }
const char *nppmac_getName(void) { return "EmptyPlugin"; }
NppMacFuncItem *nppmac_getFuncsArray(int *count) { *count = 0; return 0; }
