/**
 * Tests for electron/desktop-uninstall.cjs.
 *
 * Run with: node --test electron/desktop-uninstall.test.cjs
 * (Wired into npm test:desktop:platforms in package.json.)
 *
 * These are the pure helpers behind the desktop Chat GUI uninstaller: the
 * mode → CLI-flag mapping, the running-app-bundle resolution per OS, and the
 * cleanup-script builders (POSIX + Windows).
 */

const test = require('node:test')
const assert = require('node:assert/strict')

const {
  UNINSTALL_MODES,
  buildPosixCleanupScript,
  buildWindowsCleanupScript,
  modeRemovesAgent,
  modeRemovesUserData,
  resolveRemovableAppPath,
  shouldRemoveAppBundle,
  uninstallArgsForMode
} = require('./desktop-uninstall.cjs')

// --- uninstallArgsForMode ---

test('uninstallArgsForMode maps each mode to the module-runner argv', () => {
  assert.deepEqual(uninstallArgsForMode('gui'), ['-m', 'sara_cli.uninstall', '--mode', 'gui'])
  assert.deepEqual(uninstallArgsForMode('lite'), ['-m', 'sara_cli.uninstall', '--mode', 'lite'])
  assert.deepEqual(uninstallArgsForMode('full'), ['-m', 'sara_cli.uninstall', '--mode', 'full'])
})

test('uninstallArgsForMode throws on an unknown mode (no silent full wipe)', () => {
  assert.throws(() => uninstallArgsForMode('nuke'), /Unknown uninstall mode/)
  assert.throws(() => uninstallArgsForMode(''), /Unknown uninstall mode/)
})

test('UNINSTALL_MODES lists exactly the three supported modes', () => {
  assert.deepEqual([...UNINSTALL_MODES].sort(), ['full', 'gui', 'lite'])
})

// --- modeRemovesAgent / modeRemovesUserData ---

test('mode predicates classify what each mode removes', () => {
  assert.equal(modeRemovesAgent('gui'), false)
  assert.equal(modeRemovesAgent('lite'), true)
  assert.equal(modeRemovesAgent('full'), true)

  assert.equal(modeRemovesUserData('gui'), false)
  assert.equal(modeRemovesUserData('lite'), false)
  assert.equal(modeRemovesUserData('full'), true)
})

// --- resolveRemovableAppPath ---

test('resolveRemovableAppPath finds the .app bundle on macOS', () => {
  assert.equal(
    resolveRemovableAppPath('/Applications/Sara.app/Contents/MacOS/Sara', 'darwin'),
    '/Applications/Sara.app'
  )
  assert.equal(
    resolveRemovableAppPath('/Users/x/Applications/Sara.app/Contents/MacOS/Sara', 'darwin'),
    '/Users/x/Applications/Sara.app'
  )
})

test('resolveRemovableAppPath: dev-run .app resolves (safety is shouldRemoveAppBundle, not null)', () => {
  // A dev run from node_modules' Electron DOES resolve to a .app — the real
  // dev-run safety gate is shouldRemoveAppBundle(isPackaged=false,...), not a
  // null return here. This test documents that contract.
  assert.equal(
    resolveRemovableAppPath('/repo/node_modules/electron/dist/Electron.app/Contents/MacOS/Electron', 'darwin'),
    '/repo/node_modules/electron/dist/Electron.app'
  )
  assert.equal(shouldRemoveAppBundle(false, '/repo/node_modules/electron/dist/Electron.app'), false)
  // A bare path with no .app ancestor → null.
  assert.equal(resolveRemovableAppPath('/usr/bin/electron', 'darwin'), null)
})

test('resolveRemovableAppPath finds the install dir on Windows', () => {
  assert.equal(
    resolveRemovableAppPath('C:\\Users\\x\\AppData\\Local\\Programs\\Sara\\Sara.exe', 'win32'),
    'C:\\Users\\x\\AppData\\Local\\Programs\\Sara'
  )
  assert.equal(
    resolveRemovableAppPath('C:\\Users\\x\\AppData\\Local\\Sara-desktop\\Sara.exe', 'win32'),
    'C:\\Users\\x\\AppData\\Local\\Sara-desktop'
  )
})

test('resolveRemovableAppPath returns null for an unrecognized Windows dir', () => {
  assert.equal(resolveRemovableAppPath('C:\\Temp\\foo\\Sara.exe', 'win32'), null)
})

test('resolveRemovableAppPath uses APPIMAGE on Linux when set', () => {
  assert.equal(
    resolveRemovableAppPath('/tmp/.mount_SaraXXXX/Sara', 'linux', { APPIMAGE: '/home/x/Apps/Sara.AppImage' }),
    '/home/x/Apps/Sara.AppImage'
  )
})

test('resolveRemovableAppPath finds the unpacked dir on Linux', () => {
  assert.equal(
    resolveRemovableAppPath('/opt/Sara/linux-unpacked/Sara', 'linux', {}),
    '/opt/Sara/linux-unpacked'
  )
  // A system-package install (/usr/bin) → null, left to apt/dnf.
  assert.equal(resolveRemovableAppPath('/usr/bin/Sara', 'linux', {}), null)
})

test('resolveRemovableAppPath returns null for an empty exe path', () => {
  assert.equal(resolveRemovableAppPath('', 'darwin'), null)
  assert.equal(resolveRemovableAppPath(null, 'win32'), null)
})

// --- shouldRemoveAppBundle ---

test('shouldRemoveAppBundle requires packaged AND a resolved path', () => {
  assert.equal(shouldRemoveAppBundle(true, '/Applications/Sara.app'), true)
  assert.equal(shouldRemoveAppBundle(false, '/Applications/Sara.app'), false)
  assert.equal(shouldRemoveAppBundle(true, null), false)
  assert.equal(shouldRemoveAppBundle(false, null), false)
})

// --- buildPosixCleanupScript ---

test('buildPosixCleanupScript waits for the PID, runs the uninstall module, removes bundle', () => {
  const script = buildPosixCleanupScript({
    desktopPid: 4321,
    pythonExe: '/home/x/.Sara/Sara-agent/venv/bin/python',
    pythonPath: null,
    agentRoot: '/home/x/.Sara/Sara-agent',
    uninstallArgs: ['-m', 'sara_cli.uninstall', '--mode', 'gui'],
    appPath: '/opt/Sara/linux-unpacked',
    SaraHome: '/home/x/.Sara'
  })
  assert.match(script, /^#!\/bin\/bash/)
  assert.match(script, /pid=4321/)
  assert.match(script, /kill -0 "\$pid"/)
  // bounded wait (~30s), not unbounded
  assert.match(script, /seq 1 60/)
  assert.match(script, /'-m' 'sara_cli\.uninstall' '--mode' 'gui'/)
  assert.match(script, /rm -rf '\/opt\/Sara\/linux-unpacked'/)
  assert.match(script, /export Sara_HOME='\/home\/x\/\.Sara'/)
})

test('buildPosixCleanupScript exports PYTHONPATH when pythonPath is set (lite/full)', () => {
  const script = buildPosixCleanupScript({
    desktopPid: 1,
    pythonExe: '/usr/bin/python3',
    pythonPath: '/home/x/.Sara/Sara-agent',
    agentRoot: '/home/x/.Sara/Sara-agent',
    uninstallArgs: ['-m', 'sara_cli.uninstall', '--mode', 'full'],
    appPath: null,
    SaraHome: '/home/x/.Sara'
  })
  // System python + source on PYTHONPATH so import Sara_cli works while the
  // venv is torn down.
  assert.match(script, /export PYTHONPATH='\/home\/x\/\.Sara\/Sara-agent'/)
  assert.match(script, /'\/usr\/bin\/python3' '-m' 'sara_cli\.uninstall' '--mode' 'full'/)
})

test('buildPosixCleanupScript omits PYTHONPATH when pythonPath is null (gui)', () => {
  const script = buildPosixCleanupScript({
    desktopPid: 1,
    pythonExe: '/p/python',
    pythonPath: null,
    agentRoot: '/a',
    uninstallArgs: ['-m', 'sara_cli.uninstall', '--mode', 'gui'],
    appPath: null,
    SaraHome: '/h'
  })
  assert.doesNotMatch(script, /export PYTHONPATH/)
})

test('buildPosixCleanupScript omits the bundle rm when appPath is null', () => {
  const script = buildPosixCleanupScript({
    desktopPid: 1,
    pythonExe: '/p/python',
    pythonPath: null,
    agentRoot: '/a',
    uninstallArgs: ['-m', 'sara_cli.uninstall', '--mode', 'lite'],
    appPath: null,
    SaraHome: '/h'
  })
  assert.doesNotMatch(script, /rm -rf '\//)
  // Still runs the uninstall.
  assert.match(script, /'-m' 'sara_cli\.uninstall' '--mode' 'lite'/)
})

test('buildPosixCleanupScript single-quote-escapes paths with apostrophes', () => {
  const script = buildPosixCleanupScript({
    desktopPid: 1,
    pythonExe: "/home/o'brien/python",
    pythonPath: null,
    agentRoot: '/a',
    uninstallArgs: ['-m', 'sara_cli.uninstall', '--mode', 'gui'],
    appPath: null,
    SaraHome: '/h'
  })
  // The apostrophe is closed-escaped-reopened so the shell sees the literal.
  assert.match(script, /'\/home\/o'\\''brien\/python'/)
})

// --- buildWindowsCleanupScript ---

test('buildWindowsCleanupScript waits (bounded) for PID, runs uninstall, rmdir bundle', () => {
  const script = buildWindowsCleanupScript({
    desktopPid: 9988,
    pythonExe: 'C:\\Python313\\python.exe',
    pythonPath: 'C:\\Sara',
    agentRoot: 'C:\\Sara',
    uninstallArgs: ['-m', 'sara_cli.uninstall', '--mode', 'full'],
    appPath: 'C:\\Users\\x\\AppData\\Local\\Programs\\Sara',
    SaraHome: 'C:\\Users\\x\\AppData\\Local\\Sara'
  })
  assert.match(script, /@echo off/)
  assert.match(script, /set "PID=9988"/)
  // PYTHONPATH set so a system python can import Sara_cli from source.
  assert.match(script, /set "PYTHONPATH=C:\\Sara;%PYTHONPATH%"/)
  assert.match(script, /"C:\\Python313\\python.exe" "-m" "sara_cli\.uninstall" "--mode" "full"/)
  // Bounded wait-loop (no infinite loop), whole-token PID match (no substring).
  assert.match(script, /if %waited% geq 60 goto waited_done/)
  assert.match(script, /findstr \/r \/c:" %PID% "/)
  assert.doesNotMatch(script, /find "%PID%"/) // the old substring-prone form is gone
  // Removal is a retry loop (Windows releases dir handles lazily).
  assert.match(script, /:rmloop/)
  assert.match(script, /rmdir \/s \/q "C:\\Users\\x\\AppData\\Local\\Programs\\Sara" >nul 2>&1/)
  assert.match(script, /if %tries% geq 10 goto rmdone/)
  assert.match(script, /del "%~f0"/)
})

test('buildWindowsCleanupScript omits PYTHONPATH + rmdir when not needed (gui, no bundle)', () => {
  const script = buildWindowsCleanupScript({
    desktopPid: 2,
    pythonExe: 'C:\\h\\venv\\Scripts\\python.exe',
    pythonPath: null,
    agentRoot: 'C:\\h',
    uninstallArgs: ['-m', 'sara_cli.uninstall', '--mode', 'gui'],
    appPath: null,
    SaraHome: 'C:\\h'
  })
  assert.doesNotMatch(script, /rmdir/)
  assert.doesNotMatch(script, /set "PYTHONPATH=/)
})
