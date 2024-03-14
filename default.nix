with import <nixpkgs> {};

let
pp = pkgs.python311Packages;
in pkgs.mkShell rec{
name = "webEvalEnv";
venvDir = "./.venv";
buildInputs = [
	pp.pip
	pkgs.zsh
];

shellHook = ''
	if [ ! -d $venvDir ]; then
		echo "Creating virtualenv..."
		python -m venv $venvDir
	fi

	echo "Activating virtualenv..."
	. $venvDir/bin/activate

	pip install -r requirements.txt

	exec zsh
'';

FLASK_APP = "app.py";
}
