{ stdenv, nodejs, pnpm, pnpmConfigHook, fetchPnpmDeps, makeBinaryWrapper, src }:

stdenv.mkDerivation (finalAttrs: {
  pname = "vastai-scraper";
  version = "1.0.0";
  inherit src;

  nativeBuildInputs = [ nodejs pnpm pnpmConfigHook makeBinaryWrapper ];

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
    makeBinaryWrapper ${nodejs}/bin/node $out/bin/vastai-scraper \
      --add-flags $out/lib/vastai-scraper/index.mjs

    runHook postInstall
  '';
})
