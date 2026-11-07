/*
 * link.h
 *
 * Okviri za komunikaciju sa ESP-om: COBS + CRC16.
 * Isti format kao ESP32/lib/link.py:  COBS( type | seq | payload | crc16_le ) 0x00
 */
#ifndef INC_LINK_H_
#define INC_LINK_H_

#include <stdint.h>
#include <stddef.h>

#define LINK_MAX_PAYLOAD 64
#define LINK_MAX_RAW     (2 + LINK_MAX_PAYLOAD + 2)          /* type + seq + payload + crc */
#define LINK_MAX_FRAME   (LINK_MAX_RAW + LINK_MAX_RAW / 254 + 2) /* posle COBS + 0x00 */

typedef struct {
	uint8_t type;
	uint8_t seq;
	uint8_t len;
	uint8_t payload[LINK_MAX_PAYLOAD];
} link_frame_t;

typedef struct {
	uint8_t buf[LINK_MAX_FRAME];
	uint16_t len;
	uint8_t overflow;
	uint32_t errors;   /* odbačeni okviri (CRC, COBS, predugački) */
} link_parser_t;

uint16_t link_crc16(const uint8_t *data, size_t n);
size_t link_cobs_encode(const uint8_t *in, size_t n, uint8_t *out);
size_t link_cobs_decode(const uint8_t *in, size_t n, uint8_t *out); /* 0 = greška */

/* Napravi ceo okvir spreman za slanje (sa 0x00 na kraju). Vraća dužinu ili 0. */
size_t link_build_frame(uint8_t type, uint8_t seq, const void *payload, size_t len, uint8_t *out);

/* Hrani parser bajt po bajt. Vraća 1 kad je u *out ispravan okvir. */
int link_parser_feed(link_parser_t *p, uint8_t byte, link_frame_t *out);

#endif /* INC_LINK_H_ */
