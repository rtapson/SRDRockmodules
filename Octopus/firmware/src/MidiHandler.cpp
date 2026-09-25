#include "MidiHandler.h"
#include <MIDI.h>

MIDI_CREATE_INSTANCE(HardwareSerial, Serial1, MidiPort);

namespace {
MidiHandler* g_handler = nullptr;

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
    current_ = number;
    relays_.setPattern(presets_.preset(number));
}

void MidiHandler::handleControlChange(uint8_t /*channel*/, uint8_t number, uint8_t value) {
    if (number < kBaseCC || number >= kBaseCC + RelayBank::kChannelCount) return;
    uint8_t index = number - kBaseCC;
    relays_.setChannel(index, value >= 64);
}
