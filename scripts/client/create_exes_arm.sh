#http://pythonhosted.org/PyInstaller/#building-the-bootloader

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

sudo apt-get install build-essential lba

cd
git clone https://github.com/pyinstaller/pyinstaller.git
cd pyinstaller/bootloader
$PROJECT_DIR/env/bin/python ./waf configure build install --no-lsb
cd ..
$PROJECT_DIR/env/bin/python setup.py install

cd $PROJECT_DIR
./create_exes.sh



