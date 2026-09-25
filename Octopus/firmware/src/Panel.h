#pragma once
#include <Arduino.h>
#include "RelayBank.h"
#include "PresetStore.h"
#include "MidiHandler.h"

// Front-panel button board (Octopus/panel): 8 CTS 228C RGB illuminated switches,
// one per output jack, on I2C0 (Teensy pins 18/19) plus an interrupt on pin 22.
//
//   LED:  off = both lines off, red = tip on, green = ring on, blue = both on.
//         Always mirrors the relays, whatever changed them (MIDI or buttons).
//   Short press (on release): step off -> red -> green -> blue -> off.
//   Hold 2 s: save all 16 lines into the last-recalled preset; LEDs flash white.
//
// If the board doesn't answer on I2C at start-up, everything else runs without it.
class Panel {
public:
    Panel(RelayBank& relays, PresetStore& presets, MidiHandler& midi);

    void begin();
    void update();
    bool present() const { return present_; }

private:
    static constexpr uint8_t kPcaRG = 0x40;    // U1: LED0-7 red, LED8-15 green
    static constexpr uint8_t kPcaB = 0x41;     // U2: LED0-7 blue
    static constexpr uint8_t kMcp = 0x20;      // U3: GP0-7 = buttons 1-8
    static constexpr uint8_t kIntPin = 22;
    static constexpr uint8_t kButtons = 8;
    static constexpr uint32_t kDebounceMs = 20;
    static constexpr uint32_t kLongPressMs = 2000;
    static constexpr uint32_t kFlashMs = 300;
    static constexpr uint32_t kPollMs = 5;
    // per-colour PWM (0-4095) to even out brightness; the resistors set the peak current
    static constexpr uint16_t kLevelRed = 4095;
    static constexpr uint16_t kLevelGreen = 4095;
    static constexpr uint16_t kLevelBlue = 4095;

    RelayBank& relays_;
    PresetStore& presets_;
    MidiHandler& midi_;

    bool present_ = false;
    uint8_t stable_ = 0;         // debounced button state, bit b = button b+1 held
    uint8_t lastRaw_ = 0;
    uint32_t lastChange_ = 0;
    uint32_t lastPoll_ = 0;
    uint32_t pressStart_[kButtons] = {};
    uint8_t longFired_ = 0;      // bit b: this hold already triggered a save
    uint32_t flashUntil_ = 0;
    int32_t shown_ = -1;         // pattern currently on the LEDs (-1 = force refresh)
    bool shownFlash_ = false;

    void pollButtons(uint32_t now);
    void onPress(uint8_t b, uint32_t now);
    void onRelease(uint8_t b);
    void cycle(uint8_t b);
    void save(uint32_t now);
    void refreshLeds(uint32_t now);
    void setChannel(uint8_t addr, uint8_t ch, uint16_t level);

    static bool probe(uint8_t addr);
    static void writeReg(uint8_t addr, uint8_t reg, uint8_t value);
    static uint8_t readReg(uint8_t addr, uint8_t reg);
};
