/* Echo test: USART2 (ST-LINK VCP), DMA prijem do IDLE linije, DMA predaja iz prstenastog bafera.
 *
 * Potrebno u CubeMX-u: USART2 460800 8N1, DMA RX i TX (Normal mode), USART2 global interrupt.
 * Poziv: echo_test_start() u main.c, posle MX_USART2_UART_Init().
 *
 * Prijem i predaja su razdvojeni prstenastim baferom, pa ST-LINK sme da isporuci podatke
 * u vise delova sa pauzama (sto i radi), a da se nista ne izgubi.
 */
#include "echo_test.h"

#include <stdint.h>

#include "main.h"

extern UART_HandleTypeDef huart2;

#define RX_CHUNK 256u
#define RING_SIZE 2048u

static uint8_t rx_buf[RX_CHUNK];
static uint8_t ring[RING_SIZE];
static volatile uint16_t ring_head = 0; /* sledece mesto za upis */
static volatile uint16_t ring_tail = 0; /* pocetak podataka koji cekaju slanje */
static volatile uint16_t tx_len = 0;    /* duzina predaje koja je u toku */
static volatile uint32_t overflow_count = 0;

static void start_rx(void)
{
    HAL_UARTEx_ReceiveToIdle_DMA(&huart2, rx_buf, RX_CHUNK);
    /* bez prekida na pola bafera: callback samo na IDLE ili pun bafer */
    __HAL_DMA_DISABLE_IT(huart2.hdmarx, DMA_IT_HT);
}

static uint16_t ring_used(void)
{
    return (uint16_t)((ring_head + RING_SIZE - ring_tail) % RING_SIZE);
}

static void kick_tx(void)
{
    if (tx_len != 0u || ring_head == ring_tail) {
        return; /* predaja vec traje ili nema sta da se salje */
    }
    /* salje se neprekinut deo do kraja bafera; ostatak u sledecem krugu */
    uint16_t len = (ring_head > ring_tail) ? (uint16_t)(ring_head - ring_tail)
                                           : (uint16_t)(RING_SIZE - ring_tail);
    tx_len = len;
    if (HAL_UART_Transmit_DMA(&huart2, &ring[ring_tail], len) != HAL_OK) {
        tx_len = 0;
    }
}

void echo_test_start(void)
{
    ring_head = ring_tail = tx_len = 0;
    start_rx();
}

void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t size)
{
    if (huart->Instance != USART2) {
        return;
    }
    for (uint16_t i = 0; i < size; ++i) {
        if (ring_used() >= RING_SIZE - 1u) {
            overflow_count++; /* bafer pun: bajt se gubi, test skripta to vidi kao gresku */
            break;
        }
        ring[ring_head] = rx_buf[i];
        ring_head = (uint16_t)((ring_head + 1u) % RING_SIZE);
    }
    start_rx();
    kick_tx();
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance != USART2) {
        return;
    }
    ring_tail = (uint16_t)((ring_tail + tx_len) % RING_SIZE);
    tx_len = 0;
    kick_tx();
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance != USART2) {
        return;
    }
    /* npr. overrun ili framing greska: ponovo pokreni prijem */
    start_rx();
}
