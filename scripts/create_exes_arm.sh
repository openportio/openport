#http://pythonhosted.org/PyInstaller/#building-the-bootloader

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

sudo apt-get install build-essential #lba

cd
rm -rf pyinstaller
git clone https://github.com/pyinstaller/pyinstaller.git
cd pyinstaller/bootloader
git reset --hard 7be200b5a6f179f6753ca5a51713f19103f23393
$PROJECT_DIR/env/bin/python ./waf configure build install --no-lsb
cd ..
$PROJECT_DIR/env/bin/python setup.py install

cd $PROJECT_DIR
./create_exes.sh



