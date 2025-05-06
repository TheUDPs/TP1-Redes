# A helper function to add color to a string message
print_colored_message() {
    shift
    printf "\e[1;33m$@\e[0m\n"
}

print_colored_message "══ Installing dependencies to compile LaTeX ══"

sudo apt install emacs
sudo apt install texlive texlive-latex-extra texlive-fonts-recommended
sudo apt install texlive-latex-recommended texlive-science texlive-pictures
sudo apt install graphviz
sudo apt install imagemagick
