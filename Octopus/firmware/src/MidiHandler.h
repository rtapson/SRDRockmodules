#pragma once
#include <Arduino.h>
#include "RelayBank.h"
#include "PresetStore.h"

// Serial-MIDI (5-pin DIN, via Serial1) input handling.
// Program Change recalls a stored preset (sets all 8 relays at once).
// Control Change (kBaseCC..kBaseCC+7) toggles a single relay live.
class MidiHandler {
public:
    static constexpr uint8_t kBaseCC = 20; // CC 20-27 -> relays 1-8

    MidiHandler(RelayBank& relays, PresetStore& presets);

    void begin();
    void update();

    // Public so the free-function MIDI library callbacks can reach them.
    void handleProgramChange(uint8_t channel, uint8_t number);
    void handleControlChange(uint8_t channel, uint8_t number, uint8_t value);

private:
    RelayBank& relays_;
    PresetStore& presets_;
};
