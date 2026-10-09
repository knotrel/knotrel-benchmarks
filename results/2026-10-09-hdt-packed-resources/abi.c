#include <stdio.h>
#include <stddef.h>
#include <sys/proc_info.h>
int main(void) { printf("%zu %zu %zu\n", sizeof(struct proc_taskinfo), offsetof(struct proc_taskinfo, pti_csw), offsetof(struct proc_taskinfo, pti_total_user)); }
