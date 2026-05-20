{
  description = "Generate pi-emote frames (OpenAI Images API)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }: let
    pkgs = nixpkgs.legacyPackages.x86_64-linux;
    py = pkgs.python312.withPackages (ps: [ ps.openai ps.pillow ps.numpy ]);
    genScript = pkgs.writeShellApplication {
      name = "generate-emotes";
      runtimeInputs = [ py pkgs.imagemagick ];
      text = ''
        export PATH="${py}/bin:$PATH"
        exec ${py}/bin/python "${self}/scripts/generate_emotes.py" "$@"
      '';
    };
  in {
    devShells = {
      x86_64-linux = {
        default = pkgs.mkShell {
          packages = [ py pkgs.imagemagick ];

          shellHook = ''
            echo "[devShell] OPENAI_API_KEY must be set in your environment"
            echo "[devShell] Example: export OPENAI_API_KEY=..."
            echo "[devShell] Run: generate-emotes --help"
          '';
        };
      };
    };

    packages = {
      x86_64-linux = {
        # So `nix shell` gives you both:
        # - a working `python` with the openai module available
        # - the `generate-emotes` helper script
        default = pkgs.buildEnv {
          name = "cyber-greymane-emote-tools";
          paths = [ py genScript ];
        };
        generate-emotes = genScript;
      };
    };

    # Convenience alias for older nix tooling.
    defaultPackage = {
      x86_64-linux = py;
    };
  };
}
