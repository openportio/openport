set -ex 
cd ../../client
bash -ex create_exes.sh
cd ../distribution/debian
bash -ex createdeb.sh
