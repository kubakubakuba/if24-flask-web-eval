with import <nixpkgs> {};

let
  pp = pkgs.python311Packages;
in pkgs.mkShell rec {
  name = "webEvalEnv";
  venvDir = "./.venv";
  
  buildInputs = [
    pkgs.python311
    pp.pip
    pkgs.zsh
    pkgs.texlive.combined.scheme-full # Full TeX Live distribution for minted
    pkgs.ghostscript # Required for pdflatex shell-escape
    pkgs.python311Packages.pygments # Ensure Pygments is available
  ];

  shellHook = ''
    if [ ! -d $venvDir ]; then
      echo "Creating virtualenv..."
      python -m venv $venvDir
    fi

    echo "Activating virtualenv..."
    . $venvDir/bin/activate

    pip install -r requirements.txt

    pip install pygments

    export PATH=/home/jakub/Documents/if24-flask-web-eval/.venv/bin:$PATH
    
    exec zsh
  '';
}
