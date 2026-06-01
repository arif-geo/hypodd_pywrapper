# HypoDD Source Modifications

The origin branch of HypoDD-2.1b has been minimally modified to ensure it successfully compiles large statically allocated arrays required for executing a 10-year catalog analysis on modern high-performance computational clusters.

## 1. Memory Model Overrides for `gfortran`

### Modfied File: 
`src/hypoDD/Makefile`

### Modifications Made:
We have injected the GCC `-mcmodel=large` argument into the `CFLAGS`, `FFLAGS`, and `LDFLAGS` flags.

### Rationale:
By default, the 64-bit GNU Fortran/C compiler restricts standard memory allocations to fit within a 32-bit (2 GB) relative addressing instruction limit. When processing extremely large arrays (which `HypoDD` uses when mapping millions of event pairs and phases), linking the compiled object code exceeds this 2GB static addressing space, generating fatal linker crashes:
> `relocation truncated to fit... collect2: error: ld returned 1 exit status`
> `additional relocation overflows omitted from the output`

Using `-mcmodel=large` tells `gcc` and `gfortran` to generate full 64-bit absolute addresses for symbols, correctly increasing the compiler memory mapping threshold to completely support our massive dataset size.