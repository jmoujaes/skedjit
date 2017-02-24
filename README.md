# Skedji It #

To get up and running with the websvc code in a VM with Ubuntu 16.04:

Required software:
sudo apt-get install python3
sudo apt-get install python3-dev
sudo apt-get install virtualenv
sudo apt-get install postgresql

Create databases in postgres for testing and development
sudo -u postgres createdb skedjit
sudo -u postgres createdb test_skedjit

To build the code and run the tests, do
cd websvc
./build.sh

That will download flask and all of its dependencies in a virtual environment. 
To activate the virtual environment, from websvc/ directory do:
source build/.env/bin/activate

To deactivate (exit) the virtual environment, do:
deactivate

To run the flask server (backend) you must have your virtual environment activated.
Then from the websvc directory, do
FLASK_APP=app.py FLASK_DEBUG=1 flask run

At this point, you can visit the create page and create an event at http://127.0.0.1:5000/create


Please update this README with instructions if it is lacking.


Configuration Notes
 - lock down postgres
 - edit postgres timezone to utc  /etc/postgresql/9.5/main/postgresql.conf



