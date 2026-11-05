/*
 * watchdog.h
 *
 * Hardverski watchdog (IWDG): ako glavna petlja ne pozove watchdog_feed() duže od
 * WATCHDOG_TIMEOUT_MS, čip se sam restartuje (umesto da ostane zaglavljen sa upaljenim motorima).
 *
 * Povezivanje: main.c, USER CODE 2 (na kraju):  watchdog_init();
 *              main.c, petlja:                  watchdog_feed();
 */
#ifndef INC_WATCHDOG_H_
#define INC_WATCHDOG_H_

#include <stdint.h>

#define WATCHDOG_ENABLE      1
/* Mora biti duže od najdužeg blokiranja glavne petlje. Sada je to front_mechanism()
 * (~3.3 s HAL_Delay). Kad mehanizam pređe na mašinu stanja, smanjiti na ~200 ms.
 * Vreme je računato za LSI = 32 kHz, ali LSI na F401 radi 17..47 kHz, pa je stvarni
 * timeout od 0.68x do 1.9x upisanog. 8190 = maksimum (4095 koraka): najmanje ~5.6 s. */
#define WATCHDOG_TIMEOUT_MS  8190

void watchdog_init(void);
void watchdog_feed(void);
uint8_t watchdog_was_reset(void);   /* 1 = poslednji restart je izazvao watchdog */

#endif /* INC_WATCHDOG_H_ */
