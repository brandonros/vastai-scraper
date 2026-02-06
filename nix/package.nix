{ stdenv, nodejs, pnpmConfigHook, fetchPnpmDeps, src }:

stdenv.mkDerivation (finalAttrs: {
  pname = "vastai-scraper";
  version = "1.0.0";
  inherit src;

  nativeBuildInputs = [ nodejs pnpmConfigHook ];

  pnpmDeps = fetchPnpmDeps {
    inherit (finalAttrs) pname version src;
    hash = "sha256-yjlQSubyAU9HoMFt+q5pcMyJg30aWni98xO6/RdfogM=";
    fetcherVersion = 3;
  };

  dontBuild = true;

  installPhase = ''
    runHook preInstall

    mkdir -p $out/lib/vastai-scraper
    cp index.mjs package.json $out/lib/vastai-scraper/
    cp -r node_modules $out/lib/vastai-scraper/

    mkdir -p $out/bin
    cat > $out/bin/vastai-scraper <<EOF
    #!/bin/sh
    exec ${nodejs}/bin/node $out/lib/vastai-scraper/index.mjs "\$@"
    EOF
    chmod +x $out/bin/vastai-scraper

    runHook postInstall
  '';
})
