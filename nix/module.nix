self:

{ config, lib, pkgs, ... }:

let
  cfg = config.services.vastai-scraper;
  package = pkgs.callPackage ./package.nix { src = self; };
in
{
  options.services.vastai-scraper = {
    enable = lib.mkEnableOption "vast.ai GPU price scraper";

    dataDir = lib.mkOption {
      type = lib.types.path;
      default = "/var/lib/vastai-scraper/data";
      description = "Directory to store CSV output files.";
    };

    schedule = lib.mkOption {
      type = lib.types.str;
      default = "*/5 * * * *";
      description = "Cron schedule for scraping.";
    };

    healthcheckUrl = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      description = "Healthchecks.io ping URL.";
    };
  };

  config = lib.mkIf cfg.enable {
    systemd.services.vastai-scraper = {
      description = "Vast.ai GPU Price Scraper";
      after = [ "network.target" ];
      wantedBy = [ "multi-user.target" ];

      environment = {
        DATA_DIR = cfg.dataDir;
        SCHEDULE = cfg.schedule;
      } // lib.optionalAttrs (cfg.healthcheckUrl != null) {
        HEALTHCHECK_URL = cfg.healthcheckUrl;
      };

      serviceConfig = {
        Type = "simple";
        ExecStart = "${package}/bin/vastai-scraper";
        Restart = "always";
        RestartSec = 10;
        DynamicUser = true;
        StateDirectory = "vastai-scraper";
      };
    };
  };
}
