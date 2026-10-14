/* Echo test za USB vezu RPi <-> Nucleo (ST-LINK VCP, USART2).
 * Sve primljene bajtove vraca nazad. Koristi ga tools/echo_test.py.
 */
#ifndef ECHO_TEST_H
#define ECHO_TEST_H

#ifdef __cplusplus
extern "C" {
#endif

void echo_test_start(void);

#ifdef __cplusplus
}
#endif

#endif /* ECHO_TEST_H */
