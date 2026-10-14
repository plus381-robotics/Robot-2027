// COBS (Consistent Overhead Byte Stuffing) enkodiranje i dekodiranje.
// Enkodirani podaci nikad ne sadrze bajt 0x00, pa se 0x00 koristi kao kraj okvira.
// Funkcije NE dodaju delimiter; to radi frame.hpp.
#pragma once

#include <cstddef>
#include <cstdint>

namespace eurobot::proto {

// Najveca moguca duzina enkodiranih podataka za ulaz od n bajtova.
constexpr size_t cobs_max_encoded_size(size_t n) { return n + n / 254 + 1; }

// Vraca broj upisanih bajtova, ili 0 ako izlazni bafer nije dovoljno velik.
inline size_t cobs_encode(const uint8_t* src, size_t len, uint8_t* dst, size_t dst_cap) {
    if (dst_cap < cobs_max_encoded_size(len)) {
        return 0;
    }
    size_t read = 0;
    size_t write = 1;
    size_t code_idx = 0;
    uint8_t code = 1;

    while (read < len) {
        if (src[read] == 0) {
            dst[code_idx] = code;
            code = 1;
            code_idx = write++;
            ++read;
        } else {
            dst[write++] = src[read++];
            ++code;
            if (code == 0xFF) {
                dst[code_idx] = code;
                code = 1;
                code_idx = write++;
            }
        }
    }
    dst[code_idx] = code;
    return write;
}

// Dekodira COBS blok (bez zavrsnog 0x00). Vraca false ako su podaci neispravni
// ili izlazni bafer premali. Duzina dekodiranih podataka ide u out_len.
inline bool cobs_decode(const uint8_t* src, size_t len, uint8_t* dst, size_t dst_cap,
                        size_t& out_len) {
    size_t read = 0;
    size_t write = 0;
    out_len = 0;

    while (read < len) {
        const uint8_t code = src[read++];
        if (code == 0) {
            return false;
        }
        for (uint8_t i = 1; i < code; ++i) {
            if (read >= len || write >= dst_cap) {
                return false;
            }
            const uint8_t b = src[read++];
            if (b == 0) {
                return false;
            }
            dst[write++] = b;
        }
        if (code != 0xFF && read < len) {
            if (write >= dst_cap) {
                return false;
            }
            dst[write++] = 0;
        }
    }
    out_len = write;
    return true;
}

}  // namespace eurobot::proto
