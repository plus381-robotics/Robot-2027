/* GENERISANO iz protocol/protocol.yaml - ne menjati ručno */
#pragma once
#include <stdint.h>

#define PROTO_VERSION 1

#define REASON_INVALID 1
#define REASON_BLOCKED 2
#define REASON_TIMEOUT 3
#define REASON_PREEMPTED 4
#define REASON_MATCH_OVER 5
#define REASON_STOPPED 6

#define GOTOFLAGS_REVERSE 1
#define GOTOFLAGS_NO_THETA 2

#define STATE_MOVING 1
#define STATE_BLOCKED 2
#define STATE_MATCH_RUNNING 4
#define STATE_MATCH_OVER 8
#define STATE_LINK_LOST 16

#define DEBUG_LIDAR 1
#define DEBUG_CONTROL 2

#define MSG_PING 0x01  /* e2n */
#define MSG_SET_POSE 0x10  /* e2n */
#define MSG_GOTO 0x11  /* e2n */
#define MSG_ROTATE 0x12  /* e2n */
#define MSG_MOVE 0x13  /* e2n */
#define MSG_STOP 0x1F  /* e2n */
#define MSG_ACTUATOR 0x20  /* e2n */
#define MSG_MATCH_START 0x30  /* e2n */
#define MSG_DEBUG_STREAMS 0x31  /* e2n */
#define MSG_PONG 0x81  /* n2e */
#define MSG_ACK 0x90  /* n2e */
#define MSG_DONE 0x91  /* n2e */
#define MSG_FAIL 0x92  /* n2e */
#define MSG_STATUS 0xA0  /* n2e */
#define MSG_LIDAR_SCAN 0xB0  /* n2e */
#define MSG_CONTROL_DEBUG 0xB1  /* n2e */
#define MSG_LOG 0xF0  /* n2e */
#define MSG_TACTIC_EVENT 0x70  /* e2h */

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
    uint8_t mask;
} msg_debug_streams_t;
_Static_assert(sizeof(msg_debug_streams_t) == 1, "DEBUG_STREAMS size");

typedef struct __attribute__((packed)) {
    uint8_t version;
} msg_pong_t;
_Static_assert(sizeof(msg_pong_t) == 1, "PONG size");

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
} msg_status_t;
_Static_assert(sizeof(msg_status_t) == 13, "STATUS size");

typedef struct __attribute__((packed)) {
    int16_t v_ref;
    int16_t v_meas;
    int16_t w_ref;
    int16_t w_meas;
    int16_t pwm_l;
    int16_t pwm_r;
} msg_control_debug_t;
_Static_assert(sizeof(msg_control_debug_t) == 12, "CONTROL_DEBUG size");
