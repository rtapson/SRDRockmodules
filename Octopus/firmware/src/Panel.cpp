#include "Panel.h"
#include <Wire.h>

namespace {
// PCA9685 registers
constexpr uint8_t kMode1 = 0x00, kMode2 = 0x01, kLed0 = 0x06, kAllLedOffH = 0xFD, kPrescale = 0xFE;
constexpr uint8_t kMode1Sleep = 0x10, kMode1AutoInc = 0x20;
// MODE2: INVRT=1, OUTDRV=0 (open drain) -- NXP PCA9685 datasheet Fig. 15, "direct LED
// connection": LED anode on +5V, cathode (via resistor) into the 5.5 V-tolerant output.
constexpr uint8_t kMode2DirectLed = 0x10;
constexpr uint8_t kPrescale1kHz = 5;       // 25 MHz / (4096 * (5 + 1)) = ~1 kHz, no visible flicker
constexpr uint8_t kFullBit = 0x10;         // bit 4 of LEDn_ON_H / LEDn_OFF_H

// MCP23017 registers, IOCON.BANK = 0 (A/B pairs interleaved)
constexpr uint8_t kIodirA = 0x00, kIodirB = 0x01, kIpolA = 0x02, kIpolB = 0x03, kGpintenA = 0x04,
                  kGpintenB = 0x05, kIntconA = 0x08, kIntconB = 0x09, kIocon = 0x0A,
                  kGppuA = 0x0C, kGppuB = 0x0D, kGpioA = 0x12, kOlatA = 0x14, kOlatB = 0x15;
constexpr uint8_t kIoconMirror = 0x40;     // INTA covers both ports
constexpr uint8_t kIoconOdr = 0x04;        // INT as open-drain (Teensy pin has a pull-up)
// GPA0-6, GPB0-6 in, GPA7/GPB7 out (driven low); pull-ups on every input
constexpr uint8_t kInputs = 0x7F;
// active-low contacts read as 1: buttons (GPA0-6, GPB0) and the encoder push (GPB3);
// the encoder's A/B (GPB1-2) are left raw for the quadrature decoder
constexpr uint8_t kIpolAValue = 0x7F, kIpolBValue = 0x09;
constexpr uint8_t kIntA = 0x7F, kIntB = 0x0F;

// Quadrature transition table, index = old AB * 4 + new AB: +1 / -1 per valid step,
// 0 for no change or a skipped (invalid) step.
constexpr int8_t kQuad[16] = {0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0};
}  // namespace

Panel::Panel(RelayBank& relays, PresetStore& presets, MidiHandler& midi)
    : relays_(relays), presets_(presets), midi_(midi) {}

bool Panel::probe(uint8_t addr) {
    Wire.beginTransmission(addr);
    return Wire.endTransmission() == 0;
}

void Panel::writeReg(uint8_t addr, uint8_t reg, uint8_t value) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    Wire.write(value);
    Wire.endTransmission();
}

// GPIOA and GPIOB in one transfer (the MCP23017 auto-increments); reading clears INT.
uint16_t Panel::readInputs() {
    Wire.beginTransmission(kMcp);
    Wire.write(kGpioA);
    Wire.endTransmission(false);
    Wire.requestFrom(kMcp, static_cast<uint8_t>(2));
    uint16_t a = Wire.available() ? Wire.read() : 0;
    uint16_t b = Wire.available() ? Wire.read() : 0;
    return a | (b << 8);
}

void Panel::begin() {
    Wire.begin();
    Wire.setClock(400000);
    present_ = probe(kPcaRG) && probe(kMcp);
    if (!present_) {
        Serial.println(F("button panel not found on I2C; running without it"));
    } else {
        writeReg(kPcaRG, kMode1, kMode1Sleep);           // prescaler only writable while asleep
        writeReg(kPcaRG, kPrescale, kPrescale1kHz);
        writeReg(kPcaRG, kMode2, kMode2DirectLed);
        writeReg(kPcaRG, kAllLedOffH, kFullBit);         // everything dark
        writeReg(kPcaRG, kMode1, kMode1AutoInc);         // wake, register auto-increment
        delayMicroseconds(500);                          // oscillator start-up

        writeReg(kMcp, kIocon, kIoconMirror | kIoconOdr);
        writeReg(kMcp, kOlatA, 0x00);
        writeReg(kMcp, kOlatB, 0x00);
        writeReg(kMcp, kIodirA, kInputs);
        writeReg(kMcp, kIodirB, kInputs);
        writeReg(kMcp, kGppuA, kInputs);
        writeReg(kMcp, kGppuB, kInputs);
        writeReg(kMcp, kIpolA, kIpolAValue);
        writeReg(kMcp, kIpolB, kIpolBValue);
        writeReg(kMcp, kIntconA, 0x00);                  // interrupt on any change
        writeReg(kMcp, kIntconB, 0x00);
        writeReg(kMcp, kGpintenA, kIntA);
        writeReg(kMcp, kGpintenB, kIntB);
        pinMode(kIntPin, INPUT_PULLUP);
        uint16_t raw = readInputs();                     // also clears any pending interrupt
        stable_ = lastRaw_ = raw & kDebounced;
        encState_ = ((raw & kEncA) ? 2 : 0) | ((raw & kEncB) ? 1 : 0);

        shown_ = -1;
        refreshLeds(millis());
    }
    display_.begin();
    refreshDisplay(millis());
}

void Panel::update() {
    uint32_t now = millis();
    if (present_) {
        // Read at once while the MCP23017 flags a change (the encoder needs every
        // transition); otherwise poll only while a button is held (long-press timing) or
        // a change is still settling, and leave the bus idle the rest of the time.
        bool flagged = digitalRead(kIntPin) == LOW;
        bool busy = stable_ != 0 || lastRaw_ != stable_;
        if (flagged || (busy && now - lastPoll_ >= kPollMs)) {
            lastPoll_ = now;
            pollInputs(now);
        }
        for (uint8_t b = 0; b < kButtons; b++) {
            if ((buttonBits(stable_) & (1u << b)) && !(longFired_ & (1u << b)) &&
                now - pressStart_[b] >= kLongPressMs) {
                longFired_ |= (1u << b);
                save(now);
            }
        }
        refreshLeds(now);
    }
    if (selecting_ && now - lastTurn_ >= kSelectTimeoutMs) selecting_ = false;
    refreshDisplay(now);
}

void Panel::pollInputs(uint32_t now) {
    uint16_t word = readInputs();
    encoderStep(word, now);
    uint16_t raw = word & kDebounced;
    if (raw != lastRaw_) {
        lastRaw_ = raw;
        lastChange_ = now;
        return;
    }
    if (raw == stable_ || now - lastChange_ < kDebounceMs) return;
    uint16_t changed = raw ^ stable_;
    uint8_t pressedButtons = buttonBits(raw), changedButtons = buttonBits(changed);
    stable_ = raw;
    for (uint8_t b = 0; b < kButtons; b++) {
        if (!(changedButtons & (1u << b))) continue;
        if (pressedButtons & (1u << b)) {
            onPress(b, now);
        } else {
            onRelease(b);
        }
    }
    if ((changed & kEncSw) && (raw & kEncSw)) encoderPush();
}

// One count per detent. Detents sit at A = B = 1 (both contacts open, with the pull-ups)
// and, on half-cycle encoders, also at A = B = 0; between two detents the contacts pass
// through two transitions (half-cycle) or four (full-cycle), so a move counts once it has
// covered at least two in the same direction -- which also rides out a missed read.
void Panel::encoderStep(uint16_t raw, uint32_t now) {
    uint8_t state = ((raw & kEncA) ? 2 : 0) | ((raw & kEncB) ? 1 : 0);
    if (state == encState_) return;
    encAccum_ += kQuad[encState_ * 4 + state];
    encState_ = state;
    if (state != 3 && !(kHalfCycleDetents && state == 0)) return;
    int8_t dir = encAccum_ >= 2 ? 1 : encAccum_ <= -2 ? -1 : 0;
    encAccum_ = 0;
    if (dir == 0) return;
    if (kEncoderReverse) dir = -dir;
    if (!selecting_) pending_ = midi_.currentPreset();
    // wraps 128 -> 1 and 1 -> 128
    pending_ = (pending_ + dir + PresetStore::kPresetCount) % PresetStore::kPresetCount;
    selecting_ = true;
    lastTurn_ = now;
}

void Panel::encoderPush() {
    if (!selecting_) return;
    selecting_ = false;
    midi_.recall(pending_);
    Serial.print(F("panel: recalled preset "));
    Serial.println(pending_ + 1);
}

void Panel::onPress(uint8_t b, uint32_t now) {
    pressStart_[b] = now;
    longFired_ &= ~(1u << b);
}

void Panel::onRelease(uint8_t b) {
    if (longFired_ & (1u << b)) return;   // that hold was a save, not a step
    cycle(b);
}

// Jack b+1: line b+1 is its tip, line b+9 its ring. State s = tip + 2*ring steps
// 0 (off) -> 1 (tip, red) -> 2 (ring, green) -> 3 (both, amber) -> 0.
void Panel::cycle(uint8_t b) {
    uint16_t p = relays_.pattern();
    uint8_t s = ((p >> b) & 1) | (((p >> (b + 8)) & 1) << 1);
    s = (s + 1) & 3;
    relays_.setChannel(b, s & 1);
    relays_.setChannel(b + 8, s & 2);
}

void Panel::save(uint32_t now) {
    uint8_t slot = midi_.currentPreset();
    presets_.setPreset(slot, relays_.pattern());
    flashUntil_ = now + kFlashMs;
    savedUntil_ = now + kSavedMs;
    selecting_ = false;
    Serial.print(F("panel: saved preset "));
    Serial.println(slot + 1);
}

void Panel::setChannel(uint8_t addr, uint8_t ch, uint16_t level) {
    uint8_t onH = 0, offL = level & 0xFF, offH = (level >> 8) & 0x0F;
    if (level == 0) {
        offL = 0;
        offH = kFullBit;          // fully off
    } else if (level >= 4095) {
        onH = kFullBit;           // fully on (no PWM)
        offL = offH = 0;
    }
    Wire.beginTransmission(addr);
    Wire.write(kLed0 + 4 * ch);   // ON_L, ON_H, OFF_L, OFF_H (auto-increment)
    Wire.write(0);
    Wire.write(onH);
    Wire.write(offL);
    Wire.write(offH);
    Wire.endTransmission();
}

// Each button's red LED shows its jack's tip line and its green LED the ring line, so
// both on reads as amber. A save blinks everything off once (buttons may all be lit).
void Panel::refreshLeds(uint32_t now) {
    bool flash = static_cast<int32_t>(flashUntil_ - now) > 0;
    uint16_t p = relays_.pattern();
    if (static_cast<int32_t>(p) == shown_ && flash == shownFlash_) return;
    for (uint8_t b = 0; b < kButtons; b++) {
        bool tip = !flash && ((p >> b) & 1), ring = !flash && ((p >> (b + 8)) & 1);
        setChannel(kPcaRG, b, tip ? kLevelRed : 0);
        setChannel(kPcaRG, 8 + b, ring ? kLevelGreen : 0);
    }
    shown_ = p;
    shownFlash_ = flash;
}

void Panel::refreshDisplay(uint32_t now) {
    uint8_t current = midi_.currentPreset();
    bool edited = relays_.pattern() != presets_.preset(current);
    if (selecting_) {
        display_.show(Display::Mode::Selecting, pending_, false);
    } else if (static_cast<int32_t>(savedUntil_ - now) > 0) {
        display_.show(Display::Mode::Saved, current, false);
    } else {
        display_.show(Display::Mode::Current, current, edited);
    }
}
