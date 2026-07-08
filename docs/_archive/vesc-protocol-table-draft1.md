---
status: droppet
audited: 2026-07-08
ground_truth: "Codebase grep: zero refs to VESC/0x02/0x03/COMM_FW_VERSION/COMM_GET_VALUES in core/, apps/, scripts/ (verified 2026-07-08). Git history: single commit 4b03bead (2026-06-29) created file as "Jarvis-forfattede docs"; no follow-up commits. Project mission: Jarvis is AI identity/memo"
---
# VESC Open Client — Autoritativ protokol-tabel (Draft 1)

**Formål:** Én sandhedskilde for alle serielle kommandoer som VESC Open Client bruger.  
**Kilde:** VESC firmware `vedderb/bldc` (`comm/packet.c`, `util/buffer.c`, `comm/commands.c`, `datatypes.h`).  
**Status:** Draft 1 — 2026-06-29. Fase 1-kommandoer prioriteret.  
**Noter:**  
- 🟢 = verificeret mod kildekode  
- 🟡 = delvist verificeret / afledt fra kontekst  
- ⚠️ = endnu ikke verificeret; kræver test mod rigtig VESC

---

## 1. Pakke-framing (packet layer)

| Felt | Værdi | Bemærkning | Status |
|------|-------|------------|--------|
| Short start | `0x02` | Payload < 256 bytes | 🟢 |
| Long start | `0x03` | Payload 256–65535 bytes | 🟢 |
| Very-long start | `0x04` | Payload > 65535 bytes | 🟢 (sjælden brug) |
| Short length | 1 byte | efter `0x02` | 🟢 |
| Long length | 2 byte (MSB first) | efter `0x03` | 🟢 |
| Payload | N byte | første byte = command ID | 🟢 |
| CRC16-CCITT | 2 byte (MSB first) | beregnet over payload (command ID + data) | 🟢 |
| Stop byte | `0x03` | altid `0x03`, også for long | 🟢 |

**Total pakke-størrelse (short):** `1 + 1 + N + 2 + 1 = N + 5` byte.  
**Total pakke-størrelse (long):** `1 + 2 + N + 2 + 1 = N + 6` byte.

### 1.1 CRC16-CCITT 🟢

```c
// Fra firmwaren (crc.c)
unsigned short crc16(unsigned char *buf, unsigned int len) {
    unsigned short crc = 0;
    for (unsigned int i = 0; i < len; i++) {
        crc ^= (unsigned short)buf[i] << 8;
        for (int j = 0; j < 8; j++) {
            if (crc & 0x8000) crc = (crc << 1) ^ 0x1021;
            else crc <<= 1;
        }
    }
    return crc;
}
```

- Polynomial: `0x1021`
- Initial value: `0x0000`
- Final XOR: none
- CRC er over **payload only** (fra og med command ID), ikke header/stop byte.

---

## 2. Float- og integer-encoding (`util/buffer.c`)

| Funksjon | Format | Størrelse | Scale / note | Status |
|----------|--------|-----------|--------------|--------|
| `buffer_append_int16` | signed int16, big-endian | 2 byte | 1:1 | 🟢 |
| `buffer_append_uint16` | unsigned int16, big-endian | 2 byte | 1:1 | 🟢 |
| `buffer_append_int32` | signed int32, big-endian | 4 byte | 1:1 | 🟢 |
| `buffer_append_uint32` | unsigned int32, big-endian | 4 byte | 1:1 | 🟢 |
| `buffer_append_float16` | int16, big-endian | 2 byte | `val * scale` | 🟢 |
| `buffer_append_float32` | int32, big-endian | 4 byte | `val * scale` | 🟢 |
| `buffer_append_float32_auto` | IEEE 754 float32, big-endian | 4 byte | ingen scale | 🟢 |
| `buffer_append_double64` | int64, big-endian | 8 byte | `val * scale` | 🟢 |
| `buffer_append_float64_auto` | IEEE 754 double64, big-endian | 8 byte | ingen scale | 🟢 |

**Big-endian betyder:** MSB først, LSB sidst.

---

## 3. Fase 1 kommandoer

### 3.1 `COMM_FW_VERSION` (cmd 24) 🟢

**Request:** payload = `[24]` (1 byte).

**Response payload format:**

| Offset | Felt | Type | Størrelse | Note |
|--------|------|------|-----------|------|
| 0 | command ID | uint8 | 1 | `0x18` = 24 |
| 1 | fw_major | uint8 | 1 | fx 6 |
| 2 | fw_minor | uint8 | 1 | fx 6 |
| 3 | hw_name | null-terminated string | variabel | fx "412", "60", "75_300" |
| 3+len | uuid_8 | uint8[12] | 12 | STM32 UUID. Sidste byte +1 for motor 2 |
| ... | pairing_done | uint8 | 1 | 0/1 |
| ... | fw_test_version | uint8 | 1 | 0 for stable |
| ... | hw_type | uint8 | 1 | `HW_TYPE_VESC` = 0 |
| ... | custom_cfg_num | uint8 | 1 |  |
| ... | has_phase_filters | uint8 | 1 | 0/1 |
| ... | qml_hw_source | uint8 | 1 | 0/1/2 |
| ... | qml_app_source | uint8 | 1 | 0/1/2 |
| ... | nrf_flags | uint8 | 1 |  |
| ... | fw_name | null-terminated string | variabel | fx "VESC_default" |
| ... | hw_crc | uint32 | 4 | main_calc_hw_crc() |

**Anvendelse:** hardware-identifikation og auto-detect.

---

### 3.2 `COMM_GET_VALUES` (cmd 4) 🟡

**Request:** payload = `[4]` (1 byte).

**Response payload format (ca. 90 byte total):**

| Offset | Felt | Type | Scale | Størrelse | Note |
|--------|------|------|-------|-----------|------|
| 0 | command ID | uint8 | — | 1 | `0x04` |
| 1 | temp_fet | float16 | ×10 | 2 | MOSFET temp, °C |
| 3 | temp_motor | float16 | ×10 | 2 | Motor temp, °C |
| 5 | current_motor | float32 | ×100 | 4 | Motor strøm, A |
| 9 | current_in | float32 | ×100 | 4 | Input strøm, A |
| 13 | id | float32 | ×100 | 4 | FOC d-axis current |
| 17 | iq | float32 | ×100 | 4 | FOC q-axis current |
| 21 | duty_now | float16 | ×1000 | 2 | Duty cycle, 0–1 |
| 23 | rpm | float32 | ×1 | 4 | Electrical RPM |
| 27 | v_in | float16 | ×10 | 2 | Input spænding, V |
| 29 | amp_hours | float32 | ×10000 | 4 | Forbrugt Ah |
| 33 | amp_hours_charged | float32 | ×10000 | 4 | Opladet Ah (regen) |
| 37 | watt_hours | float32 | ×10000 | 4 | Forbrugt Wh |
| 41 | watt_hours_charged | float32 | ×10000 | 4 | Opladet Wh |
| 45 | tachometer | int32 | ×1 | 4 | Tæller |
| 49 | tachometer_abs | int32 | ×1 | 4 | Absolut tæller |
| 53 | fault_code | int8 | — | 1 | Se fault-code tabel |
| 54 | pid_pos | float32? | ? | 4 | Position |
| 58 | controller_id | uint8 | — | 1 | CAN ID |
| 59 | temp_fet_filtered | float16? | ? | 2 |  |
| 61 | temp_motor_filtered | float16? | ? | 2 |  |
| 63 | v_in_filtered | float16? | ? | 2 |  |
| 65 | rpm_observer | float32? | ? | 4 |  |
| 69 | current_id_filtered | float32? | ? | 4 |  |
| 73 | current_iq_filtered | float32? | ? | 4 |  |
| 77 | ... | ... | ... | ... | Firmware-afhængige ekstra felter |

**Status:** Øvre del (offset 0–58) er 🟡 baseret på PyVESC og eksisterende dokumentation. Nøjagtig rækkefølge, scales og felt-størrelser for offset > 58 kræver verifikation mod aktuel firmware. **Denne tabel må ikke kodes efter før den er verificeret mod en rigtig GET_VALUES-dump.**

---

### 3.3 `COMM_GET_VALUES_SELECTIVE` (cmd 77) 🟢

**Request format:**

| Offset | Felt | Type | Størrelse | Note |
|--------|------|------|-----------|------|
| 0 | command ID | uint8 | 1 | `0x4D` = 77 |
| 1 | mask | uint32 | 4 | Bitmask for hvilke felter der ønskes |

**Response:** samme format som `COMM_GET_VALUES`, men kun de felter der er valgt i masken returneres. Rækkefølgen følger stadig den originale tabel.

**Masken er én uint32** — ikke en byte-serie. Verificeret mod `commands.c`.

---

### 3.4 `COMM_SET_CURRENT` (cmd 6) 🟢

**Request format:**

| Offset | Felt | Type | Størrelse | Note |
|--------|------|------|-----------|------|
| 0 | command ID | uint8 | 1 | `0x06` |
| 1 | current | float32 | 4 | A, big-endian IEEE 754 float32_auto |

**Response:** ack — typisk tom payload eller `[command_id]`. Ingen command ID i payload ifølge VESC Tool kode.

---

### 3.5 `COMM_SET_CURRENT_BRAKE` (cmd 7) 🟢

| Offset | Felt | Type | Størrelse | Note |
|--------|------|------|-----------|------|
| 0 | command ID | uint8 | 1 | `0x07` |
| 1 | current | float32 | 4 | Negativ brake current, A |

---

### 3.6 `COMM_SET_DUTY` (cmd 8) 🟢

| Offset | Felt | Type | Størrelse | Note |
|--------|------|------|-----------|------|
| 0 | command ID | uint8 | 1 | `0x08` |
| 1 | duty | float32 | 4 | -1.0 til 1.0 |

---

### 3.7 `COMM_SET_RPM` (cmd 10) 🟢

| Offset | Felt | Type | Størrelse | Note |
|--------|------|------|-----------|------|
| 0 | command ID | uint8 | 1 | `0x0A` |
| 1 | rpm | int32 | 4 | Electrical RPM |

---

### 3.8 `COMM_GET_MCCONF` (cmd 14) 🟡

**Request:** payload = `[14]`.

**Response:** Returnerer den komplette `mc_configuration` struct som en serialiseret byte-stream. Størrelse er firmware-afhængig, typisk 200–400 byte. Kræver **long packet framing** (`0x03`).

**Encoding:** `mc_configuration` felter serialiseres med `buffer_append_*`-funktionerne (scaled ints for floats, rå ints/uints for heltal, enums som uint8).

**Status:** 🟡 — strukturen er dokumenteret i `confgenerator.h` og `datatypes.h`, men den præcise rækkefølge af felter i den serialiserede form skal genereres fra `confgenerator.c`/`confparser.c`.

---

### 3.9 `COMM_SET_MCCONF` (cmd 13) 🟢

**Request:** Serialiseret `mc_configuration` struct, prefixed med command ID `0x0D`.

**Response:** ack.

---

### 3.10 `COMM_GET_APPCONF` (cmd 16) 🟡

Samme princip som `COMM_GET_MCCONF`, men for `app_configuration` struct. Ligeledes long packet.

---

### 3.11 `COMM_SET_APPCONF` (cmd 15) 🟢

**Request:** Serialiseret `app_configuration` struct, prefixed med command ID `0x0F`.

**Response:** ack.

---

### 3.12 `COMM_TERMINAL_CMD` (cmd 20) 🟢

**Request:**

| Offset | Felt | Type | Størrelse | Note |
|--------|------|------|-----------|------|
| 0 | command ID | uint8 | 1 | `0x14` |
| 1..N | command string | ASCII bytes | variabel | uden null-terminator |

**Response:** ASCII tekst (null-termineret eller linje-baseret). Ikke binær. Bruges til `fw_info`, `hw_status`, `faults`, `foc_detect_apply_all_can`.

---

### 3.13 `COMM_FORWARD_CAN` (cmd 34) 🟡

**Request format:**

| Offset | Felt | Type | Størrelse | Note |
|--------|------|------|-----------|------|
| 0 | command ID | uint8 | 1 | `0x22` = 34 |
| 1 | can_id | uint8 | 1 | Slave CAN ID |
| 2..N | forwarded_payload | bytes | variabel | Den oprindelige kommando (fx `COMM_GET_VALUES`) |

**Response:** ⚠️ **IKKE verificeret** om svaret er wrappet eller uwrappet. Dette er en af de punkter Claude markerede som kritisk (C3). Skal testes mod rigtig dual-VESC setup før implementering.

---

### 3.14 `COMM_GET_DECODED_PPM` (cmd 31) 🟡

| Offset | Felt | Type | Størrelse | Note |
|--------|------|------|-----------|------|
| 0 | command ID | uint8 | 1 | `0x1F` |
| 1 | ppm_value | float32 | 4 |  |
| 5 | ppm_last_age | ? | ? |  |

**Status:** 🟡 — præcis størrelse og rækkefølge kræver verifikation.

---

### 3.15 `COMM_GET_DECODED_ADC` (cmd 32) 🟡

| Offset | Felt | Type | Størrelse | Note |
|--------|------|------|-----------|------|
| 0 | command ID | uint8 | 1 | `0x20` |
| 1 | adc_value | float32 | 4 |  |
| ... | adc_value2 | ? | ? |  |

**Status:** 🟡

---

### 3.16 `COMM_GET_DECODED_CHUK` (cmd 33) 🟡

| Offset | Felt | Type | Størrelse | Note |
|--------|------|------|-----------|------|
| 0 | command ID | uint8 | 1 | `0x21` |
| 1 | chuk_value | float32 | 4 |  |
| ... | yostick | ? | ? |  |

**Status:** 🟡

---

### 3.17 `COMM_GET_FAULT_CODES` (cmd 25) 🟡

**Request:** payload = `[25]`.

**Response:** Serie af int8 fault codes (null-termineret?). Status 🟡 — præcis format kræver verifikation.

---

## 4. Kommando-ID tabel (komplet)

| ID | Navn | Beskrivelse | Fase |
|----|------|-------------|------|
| 0 | COMM_FW_VERSION | Firmware og hardware info | 1 |
| 1 | COMM_JUMP_TO_BOOTLOADER |  | ❌ |
| 2 | COMM_ERASE_NEW_APP |  | ❌ |
| 3 | COMM_WRITE_NEW_APP_DATA |  | ❌ |
| 4 | COMM_GET_VALUES | Fuld telemetri | 1 |
| 5 | COMM_SET_DUTY | Set duty cycle | 1 |
| 6 | COMM_SET_CURRENT | Set strøm | 1 |
| 7 | COMM_SET_CURRENT_BRAKE | Set bremsestrøm | 1 |
| 8 | COMM_SET_RPM | Set RPM | 1 |
| 9 | COMM_SET_POS | Set position | 2 |
| 10 | COMM_SET_HANDBRAKE |  | 2 |
| 11 | COMM_SET_DETECT |  | 2 |
| 12 | COMM_SET_SERVO_POS |  | 2 |
| 13 | COMM_SET_MCCONF | Write motor config | 2 |
| 14 | COMM_GET_MCCONF | Read motor config | 2 |
| 15 | COMM_SET_APPCONF | Write app config | 2 |
| 16 | COMM_GET_APPCONF | Read app config | 2 |
| 17 | COMM_GET_MCCONF_DEFAULT | Factory motor defaults | 2 |
| 18 | COMM_GET_APPCONF_DEFAULT | Factory app defaults | 2 |
| 19 | COMM_SAMPLE_PRINT |  | 3 |
| 20 | COMM_TERMINAL_CMD | Terminal/string commands | 1 |
| 21 | COMM_PRINT |  | ❌ |
| 22 | COMM_ROTOR_POSITION |  | 3 |
| 23 | COMM_EXPERIMENT_SAMPLE |  | 3 |
| 24 | COMM_REBOOT |  | ❌ |
| 25 | COMM_GET_FAULT_CODES | Historiske faults | 2 |
| 26 | COMM_GET_FW_VERSION |  | (samme som 0?) |
| ... | ... | ... | ... |
| 34 | COMM_FORWARD_CAN | CAN forwarding | 2 |
| 77 | COMM_GET_VALUES_SELECTIVE | Selective telemetri | 2 |

---

## 5. Usikkerheder der skal løses før Fase 1-kodning

1. **COMM_GET_VALUES felt-layout for offset > 58.** Skal verificeres mod en dump fra en rigtig VESC med kendt firmware version.
2. **COMM_FORWARD_CAN response format.** Skal testes på HW 410 dual-controller setup.
3. **COMM_GET_VALUES_SELECTIVE mask-bitmapping.** uint32 er bekræftet, men hvilket bit svarer til hvilket felt er ikke.
4. **mc_configuration serialisering.** Skal genereres automatisk fra `confgenerator.c`.
5. **Decoded PPM/ADC/CHUK præcise formater.** Skal testes.

---

## 6. Next step

Før Fase 1: capture én `COMM_GET_VALUES`-dump fra Bjørns VESC og sammenlign med denne tabel. Opdater tabellen med de faktiske offset/scales. Først derefter skrives parser-koden.
