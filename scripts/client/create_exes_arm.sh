#http://pythonhosted.org/PyInstaller/#building-the-bootloader
sudo apt-get install build-essential lba

cd
git clone https://github.com/pyinstaller/pyinstaller.git
cd pyinstaller/bootloader
/home/pi/openport/openport-client/scripts/client/env/bin/python ./waf configure build install --no-lsb
cd ..
../openport/openport-client/scripts/client/env/bin/python setup.py install

cd ../openport/openport-client/scripts/client
./create_exes.sh



