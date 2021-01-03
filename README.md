# lagoon
Concise layer on top of subprocess, similar to sh project

## Install
These are generic installation instructions.

### To use, permanently
The quickest way to get started is to install the current release from PyPI:
```
pip3 install --user lagoon
```

### To use, temporarily
If you prefer to keep .local clean, install to a virtualenv:
```
python3 -m venv venvname
venvname/bin/pip install lagoon
. venvname/bin/activate
```

### To develop
First clone the repo using HTTP or SSH:
```
git clone https://github.com/combatopera/lagoon.git
git clone git@github.com:combatopera/lagoon.git
```
Now use pyven's pipify to create a setup.py, which pip can then use to install the project editably:
```
python3 -m venv pyvenvenv
pyvenvenv/bin/pip install pyven
pyvenvenv/bin/pipify lagoon

python3 -m venv venvname
venvname/bin/pip install -e lagoon
. venvname/bin/activate
```
