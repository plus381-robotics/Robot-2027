/*
 * link.c
 *
 * COBS + CRC16-CCITT (poly 0x1021, init 0xFFFF). Mora da se poklapa sa ESP32/lib/link.py.
 * Ne zavisi od HAL-a, pa može da se testira i na računaru.
 */
#include <string.h>
#include "link.h"

uint16_t link_crc16(const uint8_t *data, size_t n) {
	uint16_t crc = 0xFFFF;
	for (size_t i = 0; i < n; i++) {
		crc ^= (uint16_t) data[i] << 8;
		for (int b = 0; b < 8; b++)
			crc = (crc & 0x8000) ? (uint16_t) ((crc << 1) ^ 0x1021) : (uint16_t) (crc << 1);
	}
	return crc;
}

size_t link_cobs_encode(const uint8_t *in, size_t n, uint8_t *out) {
	size_t code_i = 0, o = 1;
	uint8_t code = 1;
	for (size_t i = 0; i < n; i++) {
		if (in[i] == 0) {
			out[code_i] = code;
			code_i = o++;
			code = 1;
		} else {
			out[o++] = in[i];
			if (++code == 0xFF) {
				out[code_i] = code;
				code_i = o++;
				code = 1;
			}
		}
	}
	out[code_i] = code;
	return o;
}

size_t link_cobs_decode(const uint8_t *in, size_t n, uint8_t *out) {
	size_t i = 0, o = 0;
	while (i < n) {
		uint8_t code = in[i++];
		if (code == 0 || i + code - 1 > n)
			return 0;
		for (uint8_t k = 1; k < code; k++)
			out[o++] = in[i++];
		if (code < 0xFF && i < n)
			out[o++] = 0;
	}
	return o;
}

size_t link_build_frame(uint8_t type, uint8_t seq, const void *payload, size_t len, uint8_t *out) {
	uint8_t raw[LINK_MAX_RAW];
	if (len > LINK_MAX_PAYLOAD)
		return 0;
	raw[0] = type;
	raw[1] = seq;
	if (len)
		memcpy(&raw[2], payload, len);
	uint16_t crc = link_crc16(raw, len + 2);
	raw[len + 2] = crc & 0xFF;
	raw[len + 3] = crc >> 8;
	size_t n = link_cobs_encode(raw, len + 4, out);
	out[n++] = 0x00;
	return n;
}

int link_parser_feed(link_parser_t *p, uint8_t byte, link_frame_t *out) {
	if (byte != 0x00) {
		if (p->len < sizeof(p->buf))
			p->buf[p->len++] = byte;
		else
			p->overflow = 1;
		return 0;
	}
	/* kraj okvira */
	uint8_t raw[LINK_MAX_FRAME];
	size_t n = 0;
	int ok = 0;
	if (p->len && !p->overflow) {
		n = link_cobs_decode(p->buf, p->len, raw);
		if (n >= 4 && n - 4 <= LINK_MAX_PAYLOAD) {
			uint16_t crc = raw[n - 2] | (raw[n - 1] << 8);
			if (link_crc16(raw, n - 2) == crc) {
				out->type = raw[0];
				out->seq = raw[1];
				out->len = (uint8_t) (n - 4);
				memcpy(out->payload, &raw[2], out->len);
				ok = 1;
			}
		}
	}
	if (!ok && (p->len || p->overflow))
		p->errors++;
	p->len = 0;
	p->overflow = 0;
	return ok;
}
