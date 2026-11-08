/* GENERISANO iz protocol/protocol.yaml - ne menjati ručno */
#pragma once
#include <stdint.h>

#define PROTO_VERSION 5

#define REASON_INVALID 1
#define REASON_BLOCKED 2
#define REASON_TIMEOUT 3
#define REASON_PREEMPTED 4
#define REASON_MATCH_OVER 5
#define REASON_STOPPED 6
#define REASON_LINK 7

#define GOTOFLAGS_REVERSE 1
#define GOTOFLAGS_NO_THETA 2

#define STATE_MOVING 1
#define STATE_BLOCKED 2
#define STATE_MATCH_RUNNING 4
#define STATE_MATCH_OVER 8

#define IR_F1 1
#define IR_F2 2
#define IR_F3 4
#define IR_F4 8
#define IR_B1 16
#define IR_B2 32
#define IR_B3 64
#define IR_B4 128

#define RESETCAUSE_PIN 1
#define RESETCAUSE_POWER 2
#define RESETCAUSE_SOFT 4
#define RESETCAUSE_IWDG 8
#define RESETCAUSE_WWDG 16
#define RESETCAUSE_LOW_POWER 32

#define MSG_PING 0x01  /* e2n */
#define MSG_SET_POSE 0x10  /* e2n */
#define MSG_GOTO 0x11  /* e2n */
#define MSG_ROTATE 0x12  /* e2n */
#define MSG_MOVE 0x13  /* e2n */
#define MSG_STOP 0x1F  /* e2n */
#define MSG_ACTUATOR 0x20  /* e2n */
#define MSG_MATCH_START 0x30  /* e2n */
#define MSG_RESUME 0x32  /* e2n */
#define MSG_ENTER_BOOTLOADER 0x40  /* e2n */
#define MSG_RESET 0x41  /* e2n */
#define MSG_IR_MASK 0x33  /* e2n */
#define MSG_PONG 0x81  /* n2e */
#define MSG_ACK 0x90  /* n2e */
#define MSG_DONE 0x91  /* n2e */
#define MSG_FAIL 0x92  /* n2e */
#define MSG_STATUS 0xA0  /* n2e */
#define MSG_LOG 0xF0  /* n2e */

typedef struct __attribute__((packed)) {
    int16_t x;
    int16_t y;
    int16_t theta;
} msg_set_pose_t;
_Static_assert(sizeof(msg_set_pose_t) == 6, "SET_POSE size");

typedef struct __attribute__((packed)) {
    int16_t x;
    int16_t y;
    int16_t theta;
    uint8_t flags;
    uint16_t max_speed;
} msg_goto_t;
_Static_assert(sizeof(msg_goto_t) == 9, "GOTO size");

typedef struct __attribute__((packed)) {
    int16_t theta;
} msg_rotate_t;
_Static_assert(sizeof(msg_rotate_t) == 2, "ROTATE size");

typedef struct __attribute__((packed)) {
    int16_t dist;
    uint16_t max_speed;
} msg_move_t;
_Static_assert(sizeof(msg_move_t) == 4, "MOVE size");

typedef struct __attribute__((packed)) {
    uint8_t id;
    int16_t value;
} msg_actuator_t;
_Static_assert(sizeof(msg_actuator_t) == 3, "ACTUATOR size");

typedef struct __attribute__((packed)) {
    int16_t x;
    int16_t y;
    int16_t theta;
    uint32_t elapsed_ms;
} msg_resume_t;
_Static_assert(sizeof(msg_resume_t) == 10, "RESUME size");

typedef struct __attribute__((packed)) {
    uint8_t mask;
} msg_ir_mask_t;
_Static_assert(sizeof(msg_ir_mask_t) == 1, "IR_MASK size");

typedef struct __attribute__((packed)) {
    uint8_t version;
    uint8_t reset_cause;
} msg_pong_t;
_Static_assert(sizeof(msg_pong_t) == 2, "PONG size");

typedef struct __attribute__((packed)) {
    uint8_t reason;
} msg_fail_t;
_Static_assert(sizeof(msg_fail_t) == 1, "FAIL size");

typedef struct __attribute__((packed)) {
    int16_t x;
    int16_t y;
    int16_t theta;
    int16_t v;
    uint8_t state;
    uint32_t match_ms;
    uint8_t last_seq;
    uint8_t last_result;
    uint32_t uptime_ms;
    int16_t w;
    uint8_t ir_raw;
    uint8_t ir_mask;
} msg_status_t;
_Static_assert(sizeof(msg_status_t) == 23, "STATUS size");
