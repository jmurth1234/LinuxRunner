#!/bin/sh
# Phoc starts this script with its Wayland and Xwayland environment.
set -eu
cd "$(dirname "$0")"
session=${LR_DESKTOP_SESSION:?}
export GDK_BACKEND=wayland QT_QPA_PLATFORM=wayland
export GSK_RENDERER=cairo GDK_GL=disable
/bin/sh ./publish-wayland-env.sh
dbus-update-activation-environment WAYLAND_DISPLAY DISPLAY XAUTHORITY XDG_RUNTIME_DIR XDG_CURRENT_DESKTOP GDK_BACKEND QT_QPA_PLATFORM GSK_RENDERER GDK_GL

# iOS controls device locking. Set Linux idle defaults once for this account.
defaults="${XDG_CONFIG_HOME:-$HOME/.config}/linuxrunner/phosh-defaults"
default_setting() {
    gsettings set "$@" || { echo "DESKTOP_STARTUP: Phosh default could not be set: $1 $2"; defaults_ok=no; }
}
if [ ! -e "$defaults" ] && [ ! -L "$defaults" ]; then
    defaults_ok=yes
    default_setting org.gnome.desktop.background picture-uri "file://$PWD/desktop-wallpaper.png"
    default_setting org.gnome.desktop.background picture-uri-dark "file://$PWD/desktop-wallpaper.png"
    default_setting org.gnome.desktop.screensaver picture-uri "file://$PWD/desktop-wallpaper.png"
    default_setting sm.puri.phosh app-filter-mode "[]"
    default_setting sm.puri.phosh favorites "['foot.desktop']"
    default_setting org.gnome.desktop.interface enable-animations false
    default_setting org.gnome.desktop.session idle-delay 0
    default_setting org.gnome.desktop.screensaver lock-enabled false
    if [ "$defaults_ok" = yes ]; then
        mkdir -p "$(dirname "$defaults")"
        printf '1\n' > "$defaults"
    fi
fi

# Replace only the original LinuxRunner favorite. Keep user changes.
favorites=$(gsettings get sm.puri.phosh favorites 2>/dev/null || true)
if [ "$favorites" = "['foot.desktop']" ]; then
    default_setting sm.puri.phosh favorites "['org.gnome.Console.desktop', 'dev.tchx84.Portfolio.desktop', 'firefox-esr.desktop', 'org.gnome.TextEditor.desktop', 'org.gnome.Calculator.desktop']"
fi
keyboard_scale=$(cat "$session/phosh-keyboard-scale" 2>/dev/null || echo 1.75)
case "$keyboard_scale" in 1|1.25|1.5|1.75|2) ;; *) keyboard_scale=1.75;; esac
keyboard=$(cat "$session/phosh-keyboard" 2>/dev/null || echo linux)
osk= shell=
cleanup() {
    trap - EXIT HUP INT TERM
    for pid in "$osk" "$shell"; do [ -z "$pid" ] || kill "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT HUP INT TERM
cd "$HOME"
echo "DESKTOP_STARTUP: phosh working-directory=$PWD"
case "$keyboard" in
    linux) default_setting org.gnome.desktop.a11y.applications screen-keyboard-enabled true
        default_setting sm.puri.Squeekboard scale-in-vertical-screen-orientation "$keyboard_scale"
        squeekboard > "$session/phosh-keyboard.log" 2>&1 & osk=$!;;
    ios) ;;
    *) echo 'DESKTOP_STARTUP: invalid Phosh keyboard'; exit 2;;
esac
/usr/libexec/phosh --unlocked & shell=$!
wait "$shell"
