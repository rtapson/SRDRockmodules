#pragma once
#include <Arduino.h>
#include "RelayBank.h"
#include "PresetStore.h"
#include "MidiHandler.h"
#include "Display.h"

// Front-panel button board (Octopus/panel) on I2C0 (Teensy pins 18/19) plus an interrupt
// on pin 22: 8 Omron B3W-9 red/green illuminated switches (one per output jack), a rotary
// encoder with push switch, and the preset display.
//
//   LED:  off = both lines off, red = tip on, green = ring on, amber (red + green) = both.
//         Always mirrors the relays, whatever changed them (MIDI, buttons or encoder).
//   Button short press (on release): step off -> red -> green -> amber -> off.
//   Button hold 2 s: save all 16 lines into the current preset; the LEDs blink off once,
//         the display says SAVED.
//   Encoder: turn to pick a preset (the display shows it under SELECT?), push to load
//         it. Leave it alone for 5 s and the display goes back to the current preset.
//
// If the LED drivers/expander don't answer at start-up, everything else runs without
// them; the display is probed separately.
class Panel {
public:
    Panel(RelayBank& relays, PresetStore& presets, MidiHandler& midi);

    void begin();
    void update();
    bool present() const { return present_; }

private:
    static constexpr uint8_t kPcaRG = 0x40;    // U1: LED0-7 red, LED8-15 green
    static constexpr uint8_t kMcp = 0x20;      // U3 MCP23017, see kEncA etc. below
    static constexpr uint8_t kIntPin = 22;
    static constexpr uint8_t kButtons = 8;
    // MCP23017 inputs as one 16-bit word (GPIOA = bits 0-7, GPIOB = bits 8-15):
    // buttons 1-7 on GPA0-6, button 8 on GPB0, encoder A/B/push on GPB1-3.
    // GPA7/GPB7 are output-only on current MCP23017 silicon, so they're not used.
    static constexpr uint16_t kEncA = 1u << 9;
    static constexpr uint16_t kEncB = 1u << 10;
    static constexpr uint16_t kEncSw = 1u << 11;
    static constexpr uint16_t kDebounced = 0x007F | 0x0100 | kEncSw;   // buttons + push
    static constexpr bool kEncoderReverse = false;   // flip if clockwise counts down
    // Alps EC11E15204A3: 15 pulses, 30 detents -- a detent every half quadrature cycle,
    // resting at A = B = 1 or A = B = 0. Set false for one-detent-per-cycle encoders
    // (e.g. Bourns PEC11R-...-S0024, 24 pulses / 24 detents), which rest at 1/1 only.
    static constexpr bool kHalfCycleDetents = true;
    static constexpr uint32_t kDebounceMs = 20;
    static constexpr uint32_t kLongPressMs = 2000;
    static constexpr uint32_t kFlashMs = 300;
    static constexpr uint32_t kSavedMs = 1500;
    static constexpr uint32_t kSelectTimeoutMs = 5000;
    static constexpr uint32_t kPollMs = 5;
    // per-colour PWM (0-4095) to balance red against green (the amber mix) and set the
    // overall brightness; the resistors set the peak currents (~10 mA red, ~16 mA green)
    static constexpr uint16_t kLevelRed = 4095;
    static constexpr uint16_t kLevelGreen = 4095;

    RelayBank& relays_;
    PresetStore& presets_;
    MidiHandler& midi_;
    Display display_;

    bool present_ = false;
    uint16_t stable_ = 0;        // debounced kDebounced bits, 1 = held
    uint16_t lastRaw_ = 0;
    uint32_t lastChange_ = 0;
    uint32_t lastPoll_ = 0;
    uint32_t pressStart_[kButtons] = {};
    uint8_t longFired_ = 0;      // bit b: this hold already triggered a save
    uint32_t flashUntil_ = 0;
    int32_t shown_ = -1;         // pattern currently on the LEDs (-1 = force refresh)
    bool shownFlash_ = false;

    uint8_t encState_ = 3;       // last A/B (bit 1 = A, bit 0 = B); 3 = both open (a detent)
    int8_t encAccum_ = 0;
    bool selecting_ = false;
    uint8_t pending_ = 0;        // preset being picked with the encoder, 0-127
    uint32_t lastTurn_ = 0;
    uint32_t savedUntil_ = 0;

    uint16_t readInputs();
    void pollInputs(uint32_t now);
    void onPress(uint8_t b, uint32_t now);
    void onRelease(uint8_t b);
    void cycle(uint8_t b);
    void save(uint32_t now);
    void encoderStep(uint16_t raw, uint32_t now);
    void encoderPush();
    void refreshLeds(uint32_t now);
    void refreshDisplay(uint32_t now);
    void setChannel(uint8_t addr, uint8_t ch, uint16_t level);

    static uint8_t buttonBits(uint16_t word) { return (word & 0x7F) | ((word >> 1) & 0x80); }
    static bool probe(uint8_t addr);
    static void writeReg(uint8_t addr, uint8_t reg, uint8_t value);
};
