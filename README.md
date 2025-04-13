# TP1-Redes

### Table of contents

1. [Mininet](#Mininet)
    1. [LinearEnds topology](#LinearEnds-topology)
    1. [Launch](#Launch)
1. [Informe](#Informe)
    1. [Compiling the PDF](#Compiling-the-PDF)
    1. [Org Mode Syntax](#Org-Mode-Syntax)
1. [Contribute](#Contribute)
    1. [Pre-commit](#Pre-commit)
    1. [Nix](#Nix)
        1. [devenv](#devenv)
        1. [direnv](#direnv)

# Mininet

## LinearEnds topology

The LineadEnds topology is a custom topology that by default has 1 host at one end, let's call it Server, and 1 host at the other end, let's call it Client, with 3 switches as intermediaries.

<p align="center">
  <img src="./docs/imgs/linear_ends_1_client.png">
</p>

There is one customization parameter for adding more hosts to the right end, a.k.a. adding more Clients.

<p align="center">
  <img src="./docs/imgs/linear_ends_multiple_clients.png">
</p>


## Launch

To launch Mininet with the LinearEnds topology execute the next command:

```bash
sudo mn --custom ./mininet/linear_ends.py --topo linends
```

To have more Client hosts, let's say `n` total client hosts, execute the next command:

```bash
sudo mn --custom ./mininet/linear_ends.py --topo linends,n
```

If you don't have Mininet run in Linux the script `scripts/install_deps.sh` or you can install visit: [Mininet website: downloads](http://mininet.org/download/).


# Informe

The informe.pdf file is generated using Org Mode that uses LaTeX to generate the PDF. To generate the PDF, you need to have some system dependencies which can be used from the Nix devenv or installed from your distribution.

You need to have Emacs and Org Mode installed on your system. You can install Emacs by following the instructions on the [Emacs website](https://www.gnu.org/software/emacs/).

Also you need to have LaTeX installed on your system. You can install LaTeX by following the instructions on the [LaTeX website](https://www.latex-project.org/get/).

## Compiling the PDF
To compile the PDF, you need to run the following command:

```bash
make
```

## Org Mode Syntax
To learn more about Org Mode syntax, you can refer to this [Org Mode Cheat Sheet](https://emacsclub.github.io/html/org_tutorial.html).

# Contribute

## Pre-commit

Pre-commit hooks are run on every commit.

To install pre-commit, run the following command:

```bash
pip install pre-commit
```

Then, run the following command to install the pre-commit hooks:

```bash
pre-commit install
```

To run all pre-commit hooks without making a commit run:

```shell
pre-commit run --all-files
```

To create a commit without running the pre-commit hooks run:

```shell
git commit --no-verify
```

## Nix

### devenv
To use the Nix development environment, you need to have Nix installed on your system. You can install Nix by following the instructions on the [Determinate Nix Installer page](https://github.com/DeterminateSystems/nix-installer).

Once you have Nix installed, you need to install devenv. You can do this by running the following command:

```bash
nix profile install nixpkgs\#devenv
```

Then, you can enter the development environment by running the following command:

```bash
devenv shell
```

### direnv

Optionally, you can install direnv to automatically load the development environment when you enter the project directory. You can do this by running the following command:

```bash
nix profile install nixpkgs\#direnv
```

Then, allow direnv to load the development environment by running the following command:

```bash
direnv allow
```

# References

- [Spear Narmox: Mininet tpology graphing tool](http://demo.spear.narmox.com/app/?apiurl=demo#!/mininet)
