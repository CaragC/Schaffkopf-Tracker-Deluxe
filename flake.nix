{
  description = "pixi env";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            (pkgs.python3.withPackages (python-pkgs: with python-pkgs; [
              fastapi
              uvicorn
              pydantic
              pandas
              requests
            ]))
          ];
        };
      }
    );
}
