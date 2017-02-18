set -eEx

rm -rf ./build/
mkdir -p build

virtualenv -p `which python` ./build/.env

cd ./build/.env
pip install -r ../../requirements.txt --no-cache-dir

cd ../../
