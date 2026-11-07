# UI audit fixes

Date: 2026-11-07. Branch: `feature/wayland-session-ui`. Audit base: `099029e`.

The Claude Opus audit identified 33 findings. This change addresses their source paths. Platform-dependent effects still need the runtime checks below. The change does not claim a measured improvement in frame rate or input latency.

## Safety and session ownership

| Audit IDs | Source change |
| --- | --- |
| UI-01, UI-04 | Desktop Settings uses the shared support installer and shows its progress. Manager settings omit actions that require a visible viewer. Repair stays disabled while a desktop runs. |
| UI-02 | Stop All Desktop Sessions asks for confirmation and warns that applications close. It also cancels a pending viewer restart. |
| UI-03 | Application windows share one environment manager and catalog state. A shared weak presentation lease prevents two manager windows from presenting the same desktop controller. The lease ends when its owning screen is released. A visible-viewer check also protects other presentation paths. |
| UI-05 | Separate buttons in desktop control rows and account rows use the borderless style. |
| UI-11 | The wizard can close while desktop support installs. The progress card offers cancellation after the current stage. Each operation has a separate cancellation request file. The guest checks it before stages and after the final stage. It does not kill a package manager during configuration. The native install guard remains active while the process runs. |
| UI-15 | The summary reports Stopping. Start and Resume remain disabled while it stops. The native start path also refuses a second session while the first stops. Stop cancels a pending restart. An intentional stop no longer becomes a startup failure. |
| UI-17 | The immersive restore control has a 44 × 44 point target. |
| UI-32 | Manager actions run from the sheet dismissal callback. Viewer actions run from the UIKit dismissal completion. The fixed 0.4 second delay is removed. |

The legacy GUI test installer and the shared support installer also check each other's native guard. The guest package lock remains in place.

Cancellation can wait for a package command, lock wait, download or build stage to finish. Completed packages stay installed. A cancelled optional desktop is not selected automatically. A cancelled final stage reports cancellation, rather than success.

## Main-thread work

| Audit IDs | Source change |
| --- | --- |
| UI-12 | Repeated native log reads use bounded asynchronous snapshots. The cache holds at most 48 entries and combines requests while a read runs. Support progress reads and parsing run on a utility queue, with one poll in flight. Audio availability has a small session status file. The last graphics route stays cached when its log line leaves the tail. |
| UI-13 | Application discovery runs in the environment manager's background loader. App Manager uses that result instead of starting a second scan. Package results and developer diagnostics load in utility tasks. Diagnostic export runs in a detached task. Package reads refuse links and special files, and allocate only the requested tail. |
| UI-14 | Debian and Arch package hashes and archive hashes run in utility tasks. Debian hashing checks cancellation between reads. Arch database extraction also runs in a utility task. |

Small session metadata reads remain bounded. Runtime start still uses the existing serialized boot path. Device profiling must check its duration before a change to that path.

## State, navigation and wording

| Audit IDs | Source change |
| --- | --- |
| UI-06 | First setup uses the initial catalog state and a persisted offered flag. A bundled Alpine root no longer suppresses the first offer. Existing catalogs do not trigger a new setup offer. |
| UI-07, UI-08 | The wizard uses DesktopChoice for optional desktop availability and installation. It does not offer Enlightenment on Debian. Wayland, Plasma and renderer text describes the implemented support. |
| UI-09 | Environment operations have separate create, remove and transfer states. Progress labels show the current operation. |
| UI-10 | Desktop selection observes shared install notifications. Installed rows refresh on success, including after navigation. The wizard also observes the shared busy state. |
| UI-16 | Desktop Settings compares the desktop requested at session start with the reported desktop. It shows a fallback notice and the desktop title. Changing a preference for the next start does not create a false fallback notice. |
| UI-18, UI-19, UI-30 | Paths and labels use the current screens. Generic device text works for iPhone and iPad. Recorded device test evidence keeps its original device name. Application Launcher and Create Launcher keep different names because they open different screens. |
| UI-20 | Linux Users, Desktop Settings and Task Manager use the catalog environment name. Distribution still identifies the Linux distribution; environment identifies an installed instance. |
| UI-21 | File Sharing has one browse/import/export destination. Home omits empty crash reports and the repeated installed-distribution list. Installed graphical applications use the Applications screen instead of repeated lists in App Manager and environment detail. Progress cards reserve space instead of covering form controls. |
| UI-22 | User and environment selection show feedback. Report export has progress and rejects repeated taps. Successful selection uses a notice state. Logging controls apply together. |
| UI-23 | The wizard and installers use the same required-space values. The wizard shows required and available storage. |
| UI-24 | Catalog installation keeps a separate pending package. Cancel leaves the search query unchanged. |
| UI-25, UI-26 | Headings and native toolbar fonts use text styles. Running state has an accessibility label. Stage changes and crash notices announce their text. Crash notices have a separate close control below the navigation bar. |
| UI-27 | Unused manager state, the unused outer file importer, the unreachable create-user dialog and unused SwiftUI screens are removed. |
| UI-28 | Login preparation errors have a separate terminal error path. The terminal shows the account error rather than a missing executable error. |
| UI-29 | Runtime and display status use plain wording. Home reads the active execution backend rather than always showing Interpreter. |
| UI-31 | The early Wayland user check uses the same legacy Debian preference fallback as session start. This consistency change does not establish that a legacy Wayland preference existed in a real installation. |
| UI-33 | Process details use the sampler's current process record. After exit, the screen identifies the retained sample and disables process actions. |

## Checks

- Release iOS simulator build.
- Native diagnostic-tail contract with AddressSanitizer and UndefinedBehaviorSanitizer: a 100 MiB sparse log, bounded reads, link and FIFO refusal, UTF-8 recovery, asynchronous refresh and deletion.
- Six support cancellation tests. They include an active stage and a request during the final stage. They do not install distribution packages.
- Nine Wayland environment tests.
- Thirteen desktop configuration tests and two desktop supervision tests.
- Foundation import/export and environment metadata contracts.
- GUI support manifest and diff whitespace checks.

## Runtime checks still required

Run these before release:

1. Open Desktop Settings from Home settings and from the viewer. Check repair progress, cancellation, alerts and return navigation.
2. Cancel the Stop All confirmation, then confirm it with disposable documents. Check that cancellation preserves the desktop.
3. Open two iPad windows. Request Desktop in both. Close the owning window and check that the other window can open Desktop.
4. Tap Fit, Actual Size, Full Screen, Set Password and Remove Account separately. Check that only the selected action runs.
5. Stop Desktop and immediately try Resume. Repeat while a restart is pending.
6. Start a desktop install, leave the screen and return before it ends. Check busy state, the installed row and the selected desktop after completion.
7. Check a clean install, Later, relaunch and setup completion. Check existing catalogs separately.
8. Check large Dynamic Type sizes, VoiceOver, portrait, landscape, Split View and external displays. Check the progress card and crash notice.
9. Measure UI pauses with large logs and a full package cache on a physical device.

Sidebar layout, a combined Desktop hub, reduced compositor effects and changes to frame transport remain design proposals. This change does not implement those proposals.
