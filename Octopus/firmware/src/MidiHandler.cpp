#include "MidiHandler.h"
#include <MIDI.h>

MIDI_CREATE_INSTANCE(HardwareSerial, Serial1, MidiPort);

namespace {
MidiHandler* g_handler = nullptr;
// Serial1's own receive buffer is 64 bytes, about 20 ms of dense MIDI at 31250 baud. The
// OLED redraws take the loop away for a few tens of ms, so give it room for ~80 ms more.
uint8_t g_rxExtra[256];

void onProgramChange(byte channel, byte number) {
    if (g_handler) g_handler->handleProgramChange(channel, number);
}

void onControlChange(byte channel, byte number, byte value) {
    if (g_handler) g_handler->handleControlChange(channel, number, value);
}
} // namespace

MidiHandler::MidiHandler(RelayBank& relays, PresetStore& presets)
    : relays_(relays), presets_(presets) {
    g_handler = this;
}

void MidiHandler::begin() {
    Serial1.addMemoryForRead(g_rxExtra, sizeof g_rxExtra);
    uint8_t channel = presets_.midiChannel();
    MidiPort.begin(channel == 0 ? MIDI_CHANNEL_OMNI : channel);
    MidiPort.setHandleProgramChange(onProgramChange);
    MidiPort.setHandleControlChange(onControlChange);
    MidiPort.turnThruOff();
}

void MidiHandler::update() {
    MidiPort.read();
}

void MidiHandler::handleProgramChange(uint8_t /*channel*/, uint8_t number) {
    recall(number);
}

void MidiHandler::recall(uint8_t preset) {
    if (preset >= PresetStore::kPresetCount) return;
    current_ = preset;
    relays_.setPattern(presets_.preset(preset));
}

void MidiHandler::handleControlChange(uint8_t /*channel*/, uint8_t number, uint8_t value) {
    if (number < kBaseCC || number >= kBaseCC + RelayBank::kChannelCount) return;
    uint8_t index = number - kBaseCC;
    relays_.setChannel(index, value >= 64);
}
