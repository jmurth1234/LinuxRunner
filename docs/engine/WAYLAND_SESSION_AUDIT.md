# Wayland session and UI audit

Date: 2026-11-06. Base: `direct-kms-display` at `2f61844`.

This is the initial audit record. The 2026-11-07 changes and remaining checks are in [UI audit fixes](UI_AUDIT_FIXES.md).

## Changes in this branch

- Publish the compositor runtime directory with its Wayland socket. Hyprland uses a shorter directory than the initial session directory. Keep the existing session bus address.
- Export the runtime directory and bus address when a launcher adopts Wayland.
- Clear stale Wayland application settings when a shell adopts X11. Keep X11 usable when the compositor socket has closed.
- Reject environment publication after the session stop marker exists, including an uncontended lock. Keep the existing check that prevents an older session from replacing a newer session's environment.
- Show the reported desktop display server and the viewer transport in session status. Do not report every Wayland desktop as Xvfb. Read the desktop state once per summary, with an 8 KiB limit.
- Replace five separate desktop installation states and five completion handlers with one installation path. Disable every install button while an installation runs. Change the selected desktop only after a successful installation.
- Put installed desktop status and installation progress in one section. Remove repeated installation footers. Keep unsupported desktops disabled in the picker and omit their install actions.
- Show the normal-user requirement for Wayland before startup, with a link to Linux Users.
- Update the manager session state only when its displayed values change. Audio counters use their own view and no longer trigger updates across all manager tabs.
- Remove the duplicate application launcher and display preference links from Settings. Applications remains on Home. Display & Gestures remains in Desktop Settings and Desktop Environment.
- Correct descriptions that said Wayland always uses software rendering. Distinguish compositor rendering from framebuffer presentation and application rendering.

## Proposed next work

These items need implementation and measurement. They are not measured performance results.

| Priority | Finding in the code | Proposed change | Required check |
| --- | --- | --- | --- |
| 1 | `LRKMSClient` polls the frame mailbox on a timer. Direct KMS still copies a full snapshot, and Metal uploads CPU pixels. | Measure idle CPU use and frame latency. Then use frame notifications and changed regions where the DRM path can supply them. Keep owned snapshots until buffer lifetime checks pass. | Compare the same workload and resolution with VNC and direct KMS. Check idle CPU, memory, frame pacing and input latency on a physical device. |
| 1 | `desktopSessionSummary` calls `audioSummary`. `audioSummary` reads the complete session log to find the audio startup marker. Manager refreshes every three seconds. | Cache the audio startup result per session, or write a small status file. Move log reads away from the main thread. | A large session log must not cause a UI pause. Preserve the unavailable-audio state and reset it for a new session. |
| 2 | Hyprland enables blur, shadows and animations when a GPU device exists. Wayfire includes animation in its initial preset. | Add a reduced-effects preference for both compositors. Respect the selected setting even when Metal is available. Keep user edits outside managed configuration blocks. | Compare frame pacing with effects on and off. Check existing user configuration files and software fallback. |
| 2 | Desktop controls dismiss a sheet and wait a fixed 0.4 seconds before the next native action. | Use presentation completion to sequence actions. | Repeatedly open controls and start, resume or reconnect with slow animations and accessibility settings. |
| 2 | Native settings still use one large `ManagerView.swift` file and several independent polling timers. | Move desktop selection and session status into separate views and a shared observable state object. Publish only changed state. | Check navigation, installation progress and status updates while switching tabs. Measure main-thread work before and after. |

See [direct KMS](DIRECT_KMS.md) for the transport design and [Wayland tests](../../tests/linuxrunner/wayland/README.md) for compositor acceptance tests.

## Validation

The environment regression tests use real Unix sockets in temporary directories on macOS. They do not start a Wayland compositor. Desktop configuration and supervision tests check shell behavior and component recovery.

Run:

```sh
python3 -m unittest discover -s tests/linuxrunner/gui -p 'test_wayland_environment.py' -v
python3 -m unittest discover -s tests/linuxrunner/gui -p 'test_desktop_*.py' -v
python3 scripts/generate-gui-support-manifest.py --check
git diff --check
```

Validation on this branch passed: 9 environment tests, 15 desktop configuration and supervision tests, the GUI support manifest check, the diff whitespace check, and the Release iOS simulator build. The simulator build checks Swift and Objective-C integration. The UI automation tool could not access Simulator, so visual layout and interaction were not checked in this session. A physical-device test must still check visual layout, touch input, compositor restart and frame pacing. No physical-device performance result is claimed by this audit.
