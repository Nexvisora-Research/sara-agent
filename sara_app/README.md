# Sara Voice

Flutter frontend for Sara Agent voice control on Linux desktop, macOS desktop,
Android, iOS, Windows, and web.

## Definition Of Done

The app is platform-ready when these commands pass on the target machine:

```bash
bash tool/setup_platforms.sh doctor
flutter pub get
flutter analyze
flutter test
flutter run -d linux      # Linux only
flutter run -d macos      # macOS only
flutter run -d android    # Android device/emulator only
```

## One-Time Platform Setup

Run the platform doctor from this directory:

```bash
cd sara_app
bash tool/setup_platforms.sh doctor
```

To install supported host packages automatically:

```bash
bash tool/setup_platforms.sh install
```

## Linux

Flutter Linux desktop requires GTK 3 development headers. The CMake error:

```text
The following required packages were not found:
 - gtk+-3.0
```

is fixed on Ubuntu/Debian with the Linux desktop package set below. The
`audioplayers_linux` plugin also requires GStreamer headers; without them you
may see:

```text
The following required packages were not found:
 - gstreamer-1.0
```

Linux microphone recording uses the `record_linux` plugin, which launches
`parecord`. If tapping the mic logs `Command: parecord ... No such file or
directory`, install `pulseaudio-utils`.

```bash
sudo apt update
sudo apt install -y clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev mesa-utils \
  libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev pulseaudio-utils
```

Then run:

```bash
flutter pub get
flutter run -d linux
```

## macOS

Install Flutter, Xcode, Xcode Command Line Tools, and CocoaPods:

```bash
xcode-select --install
brew install cocoapods
flutter doctor -v
flutter run -d macos
```

The macOS target includes microphone and network client entitlements for Sara
Voice Gateway access.

## Android

Install Android Studio and SDK components:

- Android SDK Platform
- Android SDK Platform-Tools
- Android SDK Build-Tools
- Android SDK Command-line Tools
- Android Emulator, if no physical phone is connected

If Flutter cannot find the SDK:

```bash
flutter config --android-sdk "$HOME/Android/Sdk"
```

Accept licenses and run:

```bash
flutter doctor --android-licenses
flutter pub get
flutter run -d android
```

On Linux, the script installs the Android command-line toolchain into
`~/Android/Sdk` to avoid mixing Ubuntu's old `android-sdk` packages with
Google's current build tools:

```bash
bash tool/setup_platforms.sh install-android
flutter doctor --android-licenses
flutter run -d android
```

If `adb` is installed but not on your shell path:

```bash
export ANDROID_HOME="$HOME/Android/Sdk"
export PATH="$ANDROID_HOME/platform-tools:$PATH"
```

If `apt update` fails because the VirtualBox repository is missing
`NO_PUBKEY A2F683C52980AECF`, repair that unrelated apt source first:

```bash
wget -q https://www.virtualbox.org/download/oracle_vbox_2016.asc -O /tmp/oracle_vbox_2016.asc
sudo install -m 0644 /tmp/oracle_vbox_2016.asc /usr/share/keyrings/oracle-virtualbox.asc
sudo apt update
```

The Android target registers Sara's native foreground-service bridge from
`MainActivity`.

## Voice Gateway

Start Sara's voice gateway before using the app:

```bash
cd ..
source .venv/bin/activate
export VOICE_ASSISTANT_ENABLED=true
sara gateway start
```

The default app connection is `ws://127.0.0.1:8765`. For Android emulator,
use `ws://10.0.2.2:8765`. For a physical Android device, use your computer's
LAN IP address and make sure the firewall allows the gateway port.

Voice commands also need an STT provider. For local, free transcription:

```bash
cd ..
source .venv/bin/activate
pip install faster-whisper
python -m voice_gateway.main
```

Without STT, the app can connect to the gateway but voice input will return a
speech-to-text setup error.
