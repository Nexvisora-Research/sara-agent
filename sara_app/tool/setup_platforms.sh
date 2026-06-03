#!/usr/bin/env bash
# Sara Voice Flutter platform setup and doctor.
#
# This script keeps platform prerequisites explicit for developers running:
#   flutter run -d linux
#   flutter run -d macos
#   flutter run -d android
#
# Usage:
#   bash tool/setup_platforms.sh doctor
#   bash tool/setup_platforms.sh install
#   bash tool/setup_platforms.sh install-android
#
# The install mode installs what it safely can with the available package
# manager. Android Studio / Android SDK setup still needs one-time user action.

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

MODE="${1:-doctor}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ANDROID_CMDLINE_TOOLS_URL="${ANDROID_CMDLINE_TOOLS_URL:-https://dl.google.com/android/repository/commandlinetools-linux-13114758_latest.zip}"

ok() {
  printf "%b✓%b %s\n" "$GREEN" "$NC" "$1"
}

warn() {
  printf "%b!%b %s\n" "$YELLOW" "$NC" "$1"
}

fail() {
  printf "%b✗%b %s\n" "$RED" "$NC" "$1"
}

info() {
  printf "%b→%b %s\n" "$CYAN" "$NC" "$1"
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

android_sdk_dir() {
  if [ -n "${ANDROID_HOME:-}" ]; then
    echo "$ANDROID_HOME"
  elif [ -n "${ANDROID_SDK_ROOT:-}" ]; then
    echo "$ANDROID_SDK_ROOT"
  else
    echo "$HOME/Android/Sdk"
  fi
}

find_sdkmanager() {
  local sdk_dir
  sdk_dir="$(android_sdk_dir)"

  if has_command sdkmanager; then
    command -v sdkmanager
  elif [ -x "$sdk_dir/cmdline-tools/latest/bin/sdkmanager" ]; then
    echo "$sdk_dir/cmdline-tools/latest/bin/sdkmanager"
  elif [ -x "$sdk_dir/cmdline-tools/19.0/bin/sdkmanager" ]; then
    echo "$sdk_dir/cmdline-tools/19.0/bin/sdkmanager"
  else
    return 1
  fi
}

apt_update_best_effort() {
  if sudo apt update; then
    return 0
  fi

  warn "apt update failed; continuing with the existing package cache"
  echo "A third-party apt repository may have a missing key or bad signature."
  echo "If install fails, fix the apt repository error printed above and retry."
}

is_linux() {
  [ "$(uname -s)" = "Linux" ]
}

is_macos() {
  [ "$(uname -s)" = "Darwin" ]
}

is_termux() {
  [ -n "${TERMUX_VERSION:-}" ] || [[ "${PREFIX:-}" == *"com.termux/files/usr"* ]]
}

install_android_cmdline_tools() {
  local sdk_dir tmp_dir zip_path
  sdk_dir="$(android_sdk_dir)"

  if find_sdkmanager >/dev/null 2>&1; then
    ok "Android command-line tools already installed"
    return 0
  fi

  if ! has_command wget || ! has_command unzip; then
    if is_linux && has_command apt; then
      apt_update_best_effort
      sudo apt install -y wget unzip ca-certificates
    else
      fail "wget and unzip are required to install Android command-line tools"
      return 1
    fi
  fi

  info "Installing Android command-line tools into $sdk_dir"
  mkdir -p "$sdk_dir/cmdline-tools"
  tmp_dir="$(mktemp -d)"
  zip_path="$tmp_dir/commandlinetools.zip"

  wget -q --show-progress "$ANDROID_CMDLINE_TOOLS_URL" -O "$zip_path"
  unzip -q "$zip_path" -d "$tmp_dir"

  if [ -e "$sdk_dir/cmdline-tools/latest" ]; then
    warn "$sdk_dir/cmdline-tools/latest already exists; leaving it in place"
  else
    mv "$tmp_dir/cmdline-tools" "$sdk_dir/cmdline-tools/latest"
  fi

  rm -rf "$tmp_dir"
  ok "Android command-line tools installed"
}

install_android_sdk_packages() {
  local sdk_dir sdkmanager_cmd
  sdk_dir="$(android_sdk_dir)"

  install_android_cmdline_tools
  sdkmanager_cmd="$(find_sdkmanager)"

  info "Installing Android SDK platform-tools, platform 36, and build-tools 36.0.0"
  yes | "$sdkmanager_cmd" --sdk_root="$sdk_dir" --licenses >/dev/null || true
  "$sdkmanager_cmd" --sdk_root="$sdk_dir" \
    "platform-tools" \
    "platforms;android-36" \
    "build-tools;36.0.0"

  info "Configuring Flutter Android SDK path: $sdk_dir"
  flutter config --android-sdk "$sdk_dir"

  ok "Android SDK installed at $sdk_dir"
  echo "Add this to your shell profile if adb is not on PATH:"
  echo "  export ANDROID_HOME=\"$sdk_dir\""
  echo "  export PATH=\"\$ANDROID_HOME/platform-tools:\$PATH\""
}

install_linux_packages() {
  if has_command clang++ && has_command cmake && has_command ninja && has_command pkg-config \
    && pkg-config --exists gtk+-3.0 \
    && pkg-config --exists gstreamer-1.0 \
    && has_command parecord; then
    ok "Linux desktop dependencies already installed"
    return 0
  fi

  info "Installing Linux desktop dependencies"

  if has_command apt; then
    apt_update_best_effort
    sudo apt install -y clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev mesa-utils \
      libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev pulseaudio-utils
  elif has_command dnf; then
    sudo dnf install -y clang cmake ninja-build pkgconf-pkg-config gtk3-devel xz-devel libstdc++-devel mesa-demos \
      gstreamer1-devel gstreamer1-plugins-base-devel pulseaudio-utils
  elif has_command pacman; then
    sudo pacman -S --needed clang cmake ninja pkgconf gtk3 xz mesa-utils gstreamer gst-plugins-base pulseaudio
  elif has_command zypper; then
    sudo zypper install -y clang cmake ninja pkg-config gtk3-devel xz-devel Mesa-demo-egl \
      gstreamer-devel gstreamer-plugins-base-devel pulseaudio-utils
  else
    fail "No supported Linux package manager found"
    echo "Install: clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev mesa-utils libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev pulseaudio-utils"
    return 1
  fi
}

install_macos_packages() {
  info "Checking macOS desktop dependencies"

  if ! xcode-select -p >/dev/null 2>&1; then
    warn "Xcode Command Line Tools are missing"
    echo "Run: xcode-select --install"
    return 1
  fi

  ok "Xcode Command Line Tools are installed"
  if has_command pod; then
    ok "CocoaPods is installed"
  elif has_command brew; then
    brew install cocoapods
  else
    warn "CocoaPods not found"
    echo "Install Homebrew, then run: brew install cocoapods"
  fi
}

install_android_packages() {
  info "Checking Android prerequisites"

  if ! has_command java; then
    if is_linux && has_command apt; then
      apt_update_best_effort
      sudo apt install -y openjdk-17-jdk
    elif is_macos && has_command brew; then
      brew install openjdk@17
    else
      warn "Java 17 is missing"
      echo "Install JDK 17 before building Android."
    fi
  fi

  install_android_sdk_packages

  if [ -z "${ANDROID_HOME:-}" ] && [ -z "${ANDROID_SDK_ROOT:-}" ]; then
    local sdk_dir
    sdk_dir="$(android_sdk_dir)"

    if [ -d "$sdk_dir" ]; then
      ok "Android SDK found at $sdk_dir"
    else
      warn "Android SDK path is not configured"
      echo "Install Android Studio, open SDK Manager, then install:"
      echo "  Android SDK Platform"
      echo "  Android SDK Platform-Tools"
      echo "  Android SDK Build-Tools"
      echo "  Android SDK Command-line Tools"
      echo ""
      echo "After install, set one of:"
      echo "  export ANDROID_HOME=\"\$HOME/Android/Sdk\""
      echo "  flutter config --android-sdk \"\$HOME/Android/Sdk\""
    fi
  else
    ok "Android SDK path is configured"
  fi
}

doctor_linux() {
  if ! is_linux; then
    return 0
  fi

  info "Linux desktop checks"
  for cmd in clang++ cmake ninja pkg-config; do
    if has_command "$cmd"; then
      ok "$cmd found"
    else
      fail "$cmd missing"
    fi
  done

  if pkg-config --exists gtk+-3.0; then
    ok "gtk+-3.0 development package found"
  else
    fail "gtk+-3.0 development package missing"
    echo "Install on Ubuntu/Debian: sudo apt install libgtk-3-dev"
  fi

  if pkg-config --exists gstreamer-1.0; then
    ok "gstreamer-1.0 development package found"
  else
    fail "gstreamer-1.0 development package missing"
    echo "Install on Ubuntu/Debian: sudo apt install libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev"
  fi

  if has_command eglinfo; then
    ok "eglinfo found"
  else
    warn "eglinfo missing; install mesa-utils if Flutter doctor asks for GPU info"
  fi

  if has_command parecord; then
    ok "parecord found"
  else
    fail "parecord missing; Linux microphone recording needs PulseAudio recorder"
    echo "Install on Ubuntu/Debian: sudo apt install pulseaudio-utils"
  fi
}

doctor_macos() {
  if ! is_macos; then
    return 0
  fi

  info "macOS desktop checks"
  if xcode-select -p >/dev/null 2>&1; then
    ok "Xcode Command Line Tools found"
  else
    fail "Xcode Command Line Tools missing"
    echo "Run: xcode-select --install"
  fi

  if has_command pod; then
    ok "CocoaPods found"
  else
    warn "CocoaPods missing; install with: brew install cocoapods"
  fi
}

doctor_android() {
  info "Android checks"

  if has_command java; then
    ok "$(java -version 2>&1 | head -n 1)"
  else
    fail "Java 17 missing"
  fi

  if [ -n "${ANDROID_HOME:-}" ]; then
    ok "ANDROID_HOME=$ANDROID_HOME"
  elif [ -n "${ANDROID_SDK_ROOT:-}" ]; then
    ok "ANDROID_SDK_ROOT=$ANDROID_SDK_ROOT"
  elif [ -d "$(android_sdk_dir)" ]; then
    ok "Android SDK found at $(android_sdk_dir)"
  else
    fail "Android SDK path missing"
    echo "Install Android Studio or set Flutter's SDK path:"
    echo "  flutter config --android-sdk \"\$HOME/Android/Sdk\""
  fi

  if has_command adb; then
    ok "adb found"
  elif [ -x "$(android_sdk_dir)/platform-tools/adb" ]; then
    ok "adb found at $(android_sdk_dir)/platform-tools/adb"
    warn "Add platform-tools to PATH for direct adb use"
    echo "  export PATH=\"$(android_sdk_dir)/platform-tools:\$PATH\""
  else
    warn "adb missing from PATH; install Android platform-tools"
  fi
}

run_flutter_doctor() {
  if has_command flutter; then
    info "Running flutter doctor"
    flutter doctor -v
  else
    fail "Flutter is not on PATH"
    echo "Install Flutter and add flutter/bin to PATH."
  fi
}

main() {
  cd "$APP_DIR"

  if is_termux; then
    warn "Termux can run Sara's Python agent, but Flutter Android builds should be done from Linux/macOS/Windows with Android SDK."
  fi

  case "$MODE" in
    doctor)
      doctor_linux
      doctor_macos
      doctor_android
      run_flutter_doctor
      ;;
    install)
      if is_linux; then
        install_linux_packages
      elif is_macos; then
        install_macos_packages
      else
        warn "Automatic desktop package install is only implemented for Linux and macOS."
      fi
      install_android_packages
      run_flutter_doctor
      ;;
    install-android)
      install_android_packages
      run_flutter_doctor
      ;;
    *)
      echo "Usage: bash tool/setup_platforms.sh [doctor|install|install-android]"
      exit 2
      ;;
  esac
}

main "$@"
