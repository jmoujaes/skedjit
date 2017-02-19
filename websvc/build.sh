set -eEx

PIP_VERSION=9.0.1

rm -rf ./build/
mkdir -p build

virtualenv -p `which python3` ./build/.env

cd ./build/.env

pip install --upgrade pip==${PIP_VERSION} 
pip install -r ../../requirements.txt --no-cache-dir

cd ../../

python -m compileall *.py

