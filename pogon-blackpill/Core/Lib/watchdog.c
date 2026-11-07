/*
 * watchdog.c
 *
 * IWDG preko registara (nije potrebno ništa uključivati u CubeMX-u).
 * LSI ~32 kHz / 64 = 500 Hz, jedan korak = 2 ms, najviše 4095 koraka (~8 s).
 * LSI nije precizan (17..47 kHz), pa je stvarno vreme 5.6 .. 15 s za maksimum.
 */
#include "main.h"
#include "watchdog.h"

static uint8_t was_reset;

void watchdog_init(void) {
	was_reset = (RCC->CSR & RCC_CSR_IWDGRSTF) ? 1 : 0;
	RCC->CSR |= RCC_CSR_RMVF;                 /* obriši oznake razloga restarta */
#if WATCHDOG_ENABLE
	DBGMCU->APB1FZ |= DBGMCU_APB1_FZ_DBG_IWDG_STOP;  /* ne restartuj dok debugger drži program */
	IWDG->KR = 0xCCCC;                         /* start */
	IWDG->KR = 0x5555;                         /* dozvoli upis u PR i RLR */
	IWDG->PR = 4;                              /* delilac 64 */
	uint32_t rl = WATCHDOG_TIMEOUT_MS / 2;
	IWDG->RLR = rl > 4095 ? 4095 : rl;
	while (IWDG->SR) {
	}
	IWDG->KR = 0xAAAA;                         /* prvo "hranjenje" */
#endif
}

void watchdog_feed(void) {
#if WATCHDOG_ENABLE
	IWDG->KR = 0xAAAA;
#endif
}

uint8_t watchdog_was_reset(void) {
	return was_reset;
}
