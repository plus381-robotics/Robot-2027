# protocol — zajednički protokol za RPi, Nucleo i Pico

Header-only C++17 biblioteka (bez heap-a, bez izuzetaka) koju koriste **svi** uređaji.
Jedan izvor istine: kada se doda ili promeni poruka, menja se ovde, i RPi i mikrokontroleri
dobijaju istu definiciju.

## Format okvira

```
na žici:  COBS( ver | type | seq_lo | seq_hi | payload ... | crc_lo | crc_hi )  0x00
```

| Polje | Veličina | Opis |
|---|---|---|
| `ver` | 1 B | verzija protokola (`kProtocolVersion`, trenutno 1) |
| `type` | 1 B | tip poruke (`MsgType` u `messages.hpp`) |
| `seq` | 2 B LE | sekvencijalni broj, svaka strana broji svoje poruke |
| `payload` | 0–64 B | sadržaj zavisi od tipa |
| `crc` | 2 B LE | CRC-16/CCITT-FALSE nad `ver..payload` |

COBS garantuje da unutar okvira nema bajta `0x00`, pa `0x00` uvek označava kraj okvira.
Prijemnik posle smeća ili prekida veze sam se sinhronizuje na sledeći `0x00`.

## Fajlovi

| Fajl | Sadržaj |
|---|---|
| `include/eurobot_protocol/crc16.hpp` | CRC-16/CCITT-FALSE (kontrola: `"123456789"` → `0x29B1`) |
| `include/eurobot_protocol/cobs.hpp` | COBS enkodiranje i dekodiranje |
| `include/eurobot_protocol/frame.hpp` | `encode_frame()` i `FrameDecoder` (bajt po bajt) |
| `include/eurobot_protocol/messages.hpp` | `MsgType` i little-endian pomoćne funkcije |
| `test/test_protocol.cpp` | testovi, pokreću se u CI-ju na svaki PR |

## Korišćenje

**RPi (ROS 2 paket):** u `package.xml` dodati `<depend>eurobot_protocol</depend>`, a u `CMakeLists.txt`:

```cmake
find_package(eurobot_protocol REQUIRED)
target_link_libraries(moj_cvor eurobot_protocol::eurobot_protocol)
```

**Nucleo / Pico (CMake projekat):**

```cmake
target_include_directories(${CMAKE_PROJECT_NAME} PRIVATE ${CMAKE_SOURCE_DIR}/../protocol/include)
```

**Primer:**

```cpp
#include <eurobot_protocol/protocol.hpp>
using namespace eurobot::proto;

// slanje
uint8_t wire[kMaxWireFrame];
size_t n = encode_frame(static_cast<uint8_t>(MsgType::kHeartbeat), seq++, nullptr, 0, wire, sizeof(wire));
write(fd, wire, n);

// prijem
FrameDecoder dec;
for (uint8_t b : primljeni_bajtovi) {
    if (dec.feed(b) == DecodeStatus::kFrameReady) {
        obradi(dec.frame());
    }
}
```

## Lokalno testiranje

```bash
cmake -S protocol -B build/protocol && cmake --build build/protocol && ctest --test-dir build/protocol
```

## Status

Okvir, COBS i CRC su završeni i testirani. Sadržaj poruka (`kGoal`, `kTelemetry`, `kActuators`, `kUiState`)
je rezervisan i definiše se u specifikaciji protokola. **Promena formata okvira znači povećanje `kProtocolVersion`
i istovremeno ažuriranje svih uređaja.**
