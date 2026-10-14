// Testovi protokola bez spoljnih biblioteka. Pokrece se preko ctest-a.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <vector>

#include "eurobot_protocol/protocol.hpp"

using namespace eurobot::proto;

static int g_failures = 0;
#define CHECK(cond)                                                       \
    do {                                                                  \
        if (!(cond)) {                                                    \
            std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);   \
            ++g_failures;                                                 \
        }                                                                 \
    } while (0)

static void test_crc_check_value() {
    const char* s = "123456789";
    CHECK(crc16_ccitt(reinterpret_cast<const uint8_t*>(s), 9) == 0x29B1);
}

static void test_cobs_roundtrip() {
    std::mt19937 rng(1234);
    for (size_t len = 0; len <= 600; ++len) {
        for (int pattern = 0; pattern < 4; ++pattern) {
            std::vector<uint8_t> src(len);
            for (auto& b : src) {
                switch (pattern) {
                    case 0: b = static_cast<uint8_t>(rng()); break;
                    case 1: b = 0x00; break;
                    case 2: b = 0xFF; break;
                    default: b = (rng() % 4 == 0) ? 0 : static_cast<uint8_t>(rng() | 1); break;
                }
            }
            std::vector<uint8_t> enc(cobs_max_encoded_size(len));
            const size_t n = cobs_encode(src.data(), len, enc.data(), enc.size());
            CHECK(n > 0);
            for (size_t i = 0; i < n; ++i) CHECK(enc[i] != 0);

            std::vector<uint8_t> dec(len + 1);
            size_t out = 0;
            CHECK(cobs_decode(enc.data(), n, dec.data(), dec.size(), out));
            CHECK(out == len);
            CHECK(std::memcmp(dec.data(), src.data(), len) == 0);
        }
    }
}

static void test_frame_roundtrip_with_garbage() {
    uint8_t payload[kMaxPayload];
    for (size_t i = 0; i < kMaxPayload; ++i) payload[i] = static_cast<uint8_t>(i * 7);
    payload[3] = 0;  // nule u payload-u moraju da prodju

    uint8_t wire[kMaxWireFrame];
    const size_t n = encode_frame(static_cast<uint8_t>(MsgType::kEcho), 0xBEEF, payload,
                                  kMaxPayload, wire, sizeof(wire));
    CHECK(n > 0 && n <= kMaxWireFrame);
    CHECK(wire[n - 1] == 0x00);

    FrameDecoder dec;
    // smece pre okvira, zavrseno nulom
    const uint8_t garbage[] = {0x13, 0x37, 0xAA, 0x00};
    for (uint8_t b : garbage) {
        auto st = dec.feed(b);
        CHECK(st != DecodeStatus::kFrameReady);
    }
    int ready = 0;
    for (size_t i = 0; i < n; ++i) {
        if (dec.feed(wire[i]) == DecodeStatus::kFrameReady) ++ready;
    }
    CHECK(ready == 1);
    CHECK(dec.frame().type == static_cast<uint8_t>(MsgType::kEcho));
    CHECK(dec.frame().seq == 0xBEEF);
    CHECK(dec.frame().payload_len == kMaxPayload);
    CHECK(std::memcmp(dec.frame().payload, payload, kMaxPayload) == 0);
}

static void test_crc_error_detected() {
    const uint8_t payload[] = {1, 2, 3, 4};
    uint8_t wire[kMaxWireFrame];
    const size_t n = encode_frame(0x01, 7, payload, sizeof(payload), wire, sizeof(wire));
    // pokvari jedan bit u sredini, pazeci da ne napravi 0x00
    wire[n / 2] ^= (wire[n / 2] == 0x01) ? 0x02 : 0x01;
    FrameDecoder dec;
    DecodeStatus last = DecodeStatus::kNeedMore;
    for (size_t i = 0; i < n; ++i) last = dec.feed(wire[i]);
    CHECK(last != DecodeStatus::kFrameReady);
}

static void test_overflow_recovers() {
    FrameDecoder dec;
    bool saw_overflow = false;
    for (size_t i = 0; i < kMaxWireFrame + 10; ++i) {
        if (dec.feed(0x55) == DecodeStatus::kOverflow) saw_overflow = true;
    }
    CHECK(saw_overflow);
    CHECK(dec.feed(0x00) == DecodeStatus::kNeedMore);  // kraj odbacenog okvira

    const uint8_t payload[] = {9};
    uint8_t wire[kMaxWireFrame];
    const size_t n = encode_frame(0x01, 1, payload, 1, wire, sizeof(wire));
    int ready = 0;
    for (size_t i = 0; i < n; ++i) {
        if (dec.feed(wire[i]) == DecodeStatus::kFrameReady) ++ready;
    }
    CHECK(ready == 1);
}

static void test_le_helpers() {
    uint8_t b[4];
    put_f32(b, -1.5f);
    CHECK(get_f32(b) == -1.5f);
    put_u16(b, 0x1234);
    CHECK(b[0] == 0x34 && b[1] == 0x12);
    CHECK(get_u16(b) == 0x1234);
}

int main() {
    test_crc_check_value();
    test_cobs_roundtrip();
    test_frame_roundtrip_with_garbage();
    test_crc_error_detected();
    test_overflow_recovers();
    test_le_helpers();
    if (g_failures == 0) {
        std::printf("Svi testovi protokola prosli.\n");
        return EXIT_SUCCESS;
    }
    std::printf("%d test(ova) palo.\n", g_failures);
    return EXIT_FAILURE;
}
