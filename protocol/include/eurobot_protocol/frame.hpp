// Okvir na zici:  COBS( [ver][type][seq_lo][seq_hi] [payload ...] [crc_lo][crc_hi] ) 0x00
// CRC-16 se racuna nad zaglavljem i payload-om. Svi visebajtni brojevi su little-endian.
#pragma once

#include <cstddef>
#include <cstdint>

#include "cobs.hpp"
#include "crc16.hpp"

namespace eurobot::proto {

constexpr uint8_t kProtocolVersion = 1;
constexpr size_t kHeaderSize = 4;
constexpr size_t kCrcSize = 2;
constexpr size_t kMaxPayload = 64;
constexpr size_t kMaxRawFrame = kHeaderSize + kMaxPayload + kCrcSize;
// Najveci okvir na zici, ukljucujuci zavrsni 0x00.
constexpr size_t kMaxWireFrame = cobs_max_encoded_size(kMaxRawFrame) + 1;

struct Frame {
    uint8_t version = 0;
    uint8_t type = 0;
    uint16_t seq = 0;
    uint8_t payload[kMaxPayload] = {};
    size_t payload_len = 0;
};

// Sastavlja okvir spreman za slanje. Vraca broj bajtova za slanje (sa 0x00 na kraju),
// ili 0 ako je payload prevelik ili izlazni bafer premali.
inline size_t encode_frame(uint8_t type, uint16_t seq, const uint8_t* payload, size_t payload_len,
                           uint8_t* out, size_t out_cap) {
    if (payload_len > kMaxPayload) {
        return 0;
    }
    uint8_t raw[kMaxRawFrame];
    raw[0] = kProtocolVersion;
    raw[1] = type;
    raw[2] = static_cast<uint8_t>(seq & 0xFF);
    raw[3] = static_cast<uint8_t>(seq >> 8);
    for (size_t i = 0; i < payload_len; ++i) {
        raw[kHeaderSize + i] = payload[i];
    }
    const size_t body = kHeaderSize + payload_len;
    const uint16_t crc = crc16_ccitt(raw, body);
    raw[body] = static_cast<uint8_t>(crc & 0xFF);
    raw[body + 1] = static_cast<uint8_t>(crc >> 8);

    if (out_cap < 1) {
        return 0;
    }
    const size_t enc = cobs_encode(raw, body + kCrcSize, out, out_cap - 1);
    if (enc == 0) {
        return 0;
    }
    out[enc] = 0x00;
    return enc + 1;
}

enum class DecodeStatus : uint8_t {
    kNeedMore,     // okvir jos nije zavrsen
    kFrameReady,   // ispravan okvir je u frame()
    kCobsError,    // neispravno COBS kodiranje
    kTooShort,     // okvir kraci od zaglavlja + CRC
    kCrcError,     // CRC se ne poklapa
    kBadVersion,   // nepoznata verzija protokola
    kOverflow,     // okvir duzi od kMaxWireFrame, odbacuje se do sledeceg 0x00
};

// Prima bajt po bajt (redosled kako stizu sa porta) i javlja kada je okvir spreman.
// Nema dinamicke memorije; bezbedno za ISR ili RT nit (jedan proizvodjac).
class FrameDecoder {
public:
    DecodeStatus feed(uint8_t byte) {
        if (byte != 0x00) {
            if (overflow_) {
                return DecodeStatus::kNeedMore;
            }
            if (len_ >= sizeof(buf_)) {
                overflow_ = true;
                return DecodeStatus::kOverflow;
            }
            buf_[len_++] = byte;
            return DecodeStatus::kNeedMore;
        }

        // 0x00 = kraj okvira
        const size_t enc_len = len_;
        const bool was_overflow = overflow_;
        len_ = 0;
        overflow_ = false;
        if (was_overflow || enc_len == 0) {
            return DecodeStatus::kNeedMore;  // prazan okvir ili kraj odbacenog
        }

        uint8_t raw[kMaxRawFrame];
        size_t raw_len = 0;
        if (!cobs_decode(buf_, enc_len, raw, sizeof(raw), raw_len)) {
            return DecodeStatus::kCobsError;
        }
        if (raw_len < kHeaderSize + kCrcSize) {
            return DecodeStatus::kTooShort;
        }
        const size_t body = raw_len - kCrcSize;
        const uint16_t rx_crc =
            static_cast<uint16_t>(raw[body] | (static_cast<uint16_t>(raw[body + 1]) << 8));
        if (crc16_ccitt(raw, body) != rx_crc) {
            return DecodeStatus::kCrcError;
        }
        if (raw[0] != kProtocolVersion) {
            return DecodeStatus::kBadVersion;
        }

        frame_.version = raw[0];
        frame_.type = raw[1];
        frame_.seq = static_cast<uint16_t>(raw[2] | (static_cast<uint16_t>(raw[3]) << 8));
        frame_.payload_len = body - kHeaderSize;
        for (size_t i = 0; i < frame_.payload_len; ++i) {
            frame_.payload[i] = raw[kHeaderSize + i];
        }
        return DecodeStatus::kFrameReady;
    }

    const Frame& frame() const { return frame_; }

    void reset() {
        len_ = 0;
        overflow_ = false;
    }

private:
    uint8_t buf_[kMaxWireFrame] = {};
    size_t len_ = 0;
    bool overflow_ = false;
    Frame frame_{};
};

}  // namespace eurobot::proto
