# TP1-Redes

# mininet

This repository contains a Mininet topology for testing the implementation of the transport protocols that we are going to implement.

To launch the Mininet topology, you need to have Mininet installed on your system. You can install Mininet by following the instructions on the [Mininet website](http://mininet.org/download/).

Then, you can launch the Mininet topology by running the following command:

```bash
sudo mn --custom ./mininet/fragtopo.py --topo fragtopo
```

This will create a topology with two hosts, one for the server and one for the client.

If you want to have more client hosts, you can run the following command:

```bash
sudo mn --custom ./mininet/fragtopo.py --topo fragtopo,NUM_CLIENTS
```

# Contribute

## pre-commit

To install pre-commit, run the following command:

```bash
pip install -r requirements.txt
```

Then, run the following command to install the pre-commit hooks:

```bash
pre-commit install
```

This will install the pre-commit hooks in your local repository. The hooks will run automatically when you commit changes to your repository.

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

## Informe

The informe.pdf file is generated using Org Mode that uses LaTeX to generate the PDF. To generate the PDF, you need to have some system dependencies which can be used from the Nix devenv or installed from your distribution.

You need to have Emacs and Org Mode installed on your system. You can install Emacs by following the instructions on the [Emacs website](https://www.gnu.org/software/emacs/).

Also you need to have LaTeX installed on your system. You can install LaTeX by following the instructions on the [LaTeX website](https://www.latex-project.org/get/).

### Compiling the PDF
To compile the PDF, you need to run the following command:

```bash
make
```

### Org Mode Syntax
To learn more about Org Mode syntax, you can refer to this [Org Mode Cheat Sheet](https://emacsclub.github.io/html/org_tutorial.html).
