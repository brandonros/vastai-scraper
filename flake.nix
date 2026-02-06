{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
    in
    {
      nixosModules.default = import ./nix/module.nix self;
      packages.${system}.default = pkgs.callPackage ./nix/package.nix { src = self; };
    };
}
