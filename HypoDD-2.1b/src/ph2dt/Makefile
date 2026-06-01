CMD     = ph2dt
CC      = gcc
FC      = gfortran 
SRCS    = $(CMD).f \
          cluster.f delaz.f ifindi.f \
          indexx.f indexxi.f sorti.f trimlen.f
CSRCS   = rpad_.c datetime_.c 
OBJS    = $(SRCS:%.f=%.o) $(CSRCS:%.c=%.o)
INCLDIR = ../../include

# ADDED -mcmodel=large for large arrays!
CFLAGS  = -O -mcmodel=large -I$(INCLDIR) 
FFLAGS  = -O -mcmodel=large -I$(INCLDIR)

LDFLAGS = -mcmodel=large

listflg = -L -c -O

all: $(CMD)

$(CMD): $(OBJS)
	$(FC) $(LDFLAGS) $(OBJS) $(LIBS) -o $@

%.o: %.f
	$(FC) $(FFLAGS) -c $(@F:.o=.f) -o $@

%.o: %.c
	$(CC) $(CFLAGS) -c $(@F:.o=.c) -o $@

clean:
	-rm -f $(CMD) *.o core a.out junk

atoangle_.o : ../../include/compat.h
atoangle_.o : ../../include/f77types.h
ph2dt.o : ../../include/ph2dt.inc
