.globl    array_start

.text
.globl _start

_start:

	la a0, array_start
	lw a1, 0x0(a0)
	lw a2, 0x4(a0)
	add a3, a1, a2
	sw a3, 0x8(a0)

	ebreak

.data
	array_start: