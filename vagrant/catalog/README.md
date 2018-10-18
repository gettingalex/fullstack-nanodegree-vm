# Item Catalog Project

As part of the Full Stack Web Developer Nanodegree with Udacity

## About 

This application is a catalog listing items in various categories. It includes user registration and authentication system. The web app allows logged in users to add new items, edit and delete the one they created. 

## Features

* Authentication and authorization with Google Sign-In OAuth API
* CRUD via SQLAlchemy and Flask
* JSON endpoints



## Running the Item Catalog Project

1. Install [Vagrant](https://www.vagrantup.com) and [VirtualBox](https://www.virtualbox.org)
2. Download/Clone the Vagrant VM file [fullstack-nanodegree-vm](https://github.com/udacity/fullstack-nanodegree-vm)
3. Launch Vagrant in the terminal with command 
```
vagrant up
```

4. Run the virtual machine with 
```
vagrant ssh
```

5. Then navigate to the shared directory
```
cd /vagrant
```

6. Navigate to fullstack-nanodegree-vm
7. Run the database_setup.py file to create the database (if you are not using the database already populated with filling values)
```
python database_setup.py
```

8. Run the application:
```
python application.py
```

9. In the browser, open [http://localhost:8000/](http://localhost:8000/) and use the interface to navigate the web app 

10. JSON request can be made at URL [http://localhost:8000/catalog.json/](http://localhost:8000/catalog.json/) for all categories and items in the database. To output a single item, add the item id where it stated insert_id#_here at the following link: http://localhost:8000//catalog/item/insert_id#_here/JSON

## Code Style

Python pycodestyle (formally pep8)


## Tech/Framework used:

* [Python](https://www.python.org)
* HTML
* [Bootstap](https://getbootstrap.com)
* [SQLite](https://www.sqlite.org/index.html)
* [Flask](http://flask.pocoo.org)
* [SQLAlquemy](https://www.sqlalchemy.org)
* [JSON](http://www.json.org)
* [VirtualBox](https://www.virtualbox.org)
* [Vagrant](https://www.vagrantup.com)
