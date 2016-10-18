#http://pythonhosted.org/PyInstaller/#building-the-bootloader

PROJECTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

#sudo apt-get install build-essential #lba

source $PROJECTDIR/env/bin/activate

cd
rm -rf pyinstaller
git clone https://github.com/pyinstaller/pyinstaller.git
cd pyinstaller/bootloader
git reset --hard 7be200b5a6f179f6753ca5a51713f19103f23393
python ./waf configure build install --no-lsb
cd ..
python setup.py install

cd $PROJECTDIR
bash -ex ./create_exes.sh




