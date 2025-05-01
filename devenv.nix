{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/basics/
  env.GREET = "devenv";

  # https://devenv.sh/packages/
  packages = with pkgs;
  let
    tex = (texlive.combine {
      inherit (texlive) scheme-small
        wrapfig amsmath ulem hyperref capt-of
        newverbs tikzpagenodes ifoddpage
        dvipng minted fvextra catchfile
        xstring framed a4wide svg trimspaces
        transparent tocbibind microtype stix
        geometry
        ;
    });
  in [
    git
    emacs
    tex
    pandoc
    graphviz
    xterm
  ] ++ (if stdenv.isLinux then [
    mininet
  ] else []);

  # https://devenv.sh/languages/
  languages.python = {
    enable = true;
    venv = {
      enable = true;
      requirements = ./requirements.txt;
    };
  };

  # https://devenv.sh/processes/
  # processes.cargo-watch.exec = "cargo-watch";

  # https://devenv.sh/services/
  # services.postgres.enable = true;

  # https://devenv.sh/scripts/
  scripts.hello.exec = ''
    echo hello from $GREET
  '';

  enterShell = ''
    xhost +SI:localuser:root
  '';

  # https://devenv.sh/tasks/
  # tasks = {
  #   "myproj:setup".exec = "mytool build";
  #   "devenv:enterShell".after = [ "myproj:setup" ];
  # };

  # https://devenv.sh/tests/
  enterTest = ''
    echo "Running tests"
    git --version | grep --color=auto "${pkgs.git.version}"
  '';

  # https://devenv.sh/git-hooks/
  # git-hooks.hooks.shellcheck.enable = true;

  # See full reference at https://devenv.sh/reference/options/
}
