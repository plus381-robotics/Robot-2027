// Tipovi poruka i pomocne funkcije za serijalizaciju payload-a.
// NACRT: konkretni payload-i (cilj, telemetrija) definisu se u specifikaciji protokola.
#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>

namespace eurobot::proto {

enum class MsgType : uint8_t {
    // Sistemske poruke (oba smera)
    kHeartbeat = 0x01,
    kBoot = 0x02,       // MCU -> RPi posle svakog starta, sa razlogom reseta
    kLog = 0x03,        // MCU -> RPi tekstualni log
    kAck = 0x04,        // potvrda komande (ID cilja)

    // Nucleo: kretanje (0x10-0x2F)
    kGoal = 0x10,       // RPi -> Nucleo, rezervisano
    kTelemetry = 0x20,  // Nucleo -> RPi, rezervisano

    // Pico: aktuatori i UI (0x30-0x4F)
    kActuators = 0x30,  // rezervisano
    kUiState = 0x40,    // rezervisano

    // Testiranje
    kEcho = 0x7F,
};

// Little-endian upis/citanje. Ne oslanja se na raspored struktura u memoriji.
inline void put_u16(uint8_t* p, uint16_t v) {
    p[0] = static_cast<uint8_t>(v);
    p[1] = static_cast<uint8_t>(v >> 8);
}
inline void put_u32(uint8_t* p, uint32_t v) {
    for (int i = 0; i < 4; ++i) p[i] = static_cast<uint8_t>(v >> (8 * i));
}
inline void put_f32(uint8_t* p, float v) {
    static_assert(sizeof(float) == 4, "float mora imati 4 bajta");
    uint32_t u;
    std::memcpy(&u, &v, 4);
    put_u32(p, u);
}
inline uint16_t get_u16(const uint8_t* p) {
    return static_cast<uint16_t>(p[0] | (static_cast<uint16_t>(p[1]) << 8));
}
inline uint32_t get_u32(const uint8_t* p) {
    uint32_t v = 0;
    for (int i = 0; i < 4; ++i) v |= static_cast<uint32_t>(p[i]) << (8 * i);
    return v;
}
inline float get_f32(const uint8_t* p) {
    const uint32_t u = get_u32(p);
    float v;
    std::memcpy(&v, &u, 4);
    return v;
}

}  // namespace eurobot::proto
