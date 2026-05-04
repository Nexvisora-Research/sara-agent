# nix/tui.nix — sara TUI (Ink/React) compiled with tsc and bundled
{ pkgs, saraNpmLib, ... }:
let
  src = ../ui-tui;
  npmDeps = pkgs.fetchNpmDeps {
    inherit src;
    hash = "sha256-a/HGI9OgVcTnZrMXA7xFMGnFoVxyHe95fulVz+WNYB0=";
  };

  npm = saraNpmLib.mkNpmPassthru { folder = "ui-tui"; attr = "tui"; pname = "sara-tui"; };

  packageJson = builtins.fromJSON (builtins.readFile (src + "/package.json"));
  version = packageJson.version;
in
pkgs.buildNpmPackage (npm // {
  pname = "sara-tui";
  inherit src npmDeps version;

  doCheck = false;
  npmFlags = [ "--legacy-peer-deps" ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out/lib/sara-tui

    cp -r dist $out/lib/sara-tui/dist

    # runtime node_modules
    cp -r node_modules $out/lib/sara-tui/node_modules

    # @sara/ink is a file: dependency, we need to copy it in fr
    rm -f $out/lib/sara-tui/node_modules/@sara/ink
    cp -r packages/sara-ink $out/lib/sara-tui/node_modules/@sara/ink

    # package.json needed for "type": "module" resolution
    cp package.json $out/lib/sara-tui/

    runHook postInstall
  '';
})
