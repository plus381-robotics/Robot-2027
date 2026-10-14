// CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, bez refleksije, xorout 0x0000.
// Kontrolna vrednost za ASCII "123456789" je 0x29B1.
// Header-only, bez heap-a i izuzetaka: isti kod radi na RPi, Nucleo i Pico.
#pragma once

#include <cstddef>
#include <cstdint>

namespace eurobot::proto {

inline uint16_t crc16_ccitt(const uint8_t* data, size_t len, uint16_t crc = 0xFFFF) {
    for (size_t i = 0; i < len; ++i) {
        crc ^= static_cast<uint16_t>(data[i]) << 8;
        for (int bit = 0; bit < 8; ++bit) {
            crc = (crc & 0x8000) ? static_cast<uint16_t>((crc << 1) ^ 0x1021)
                                 : static_cast<uint16_t>(crc << 1);
        }
    }
    return crc;
}

}  // namespace eurobot::proto
