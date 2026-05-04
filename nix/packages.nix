# nix/packages.nix — sara Agent package built with uv2nix
{ inputs, ... }:
{
  perSystem =
    { pkgs, inputs', ... }:
    let
      saraAgent = pkgs.callPackage ./sara-agent.nix {
        inherit (inputs) uv2nix pyproject-nix pyproject-build-systems;
        npm-lockfile-fix = inputs'.npm-lockfile-fix.packages.default;
        # Only embed clean revs — dirtyRev doesn't represent any upstream
        # commit, so comparing it would always claim "update available".
        rev = inputs.self.rev or null;
      };
    in
    {
      packages = {
        default = saraAgent;
        tui = saraAgent.saraTui;
        web = saraAgent.saraWeb;

        fix-lockfiles = saraAgent.saraNpmLib.mkFixLockfiles {
          packages = [ saraAgent.saraTui saraAgent.saraWeb ];
        };
      };
    };
}
