database
=========

Installs and configures the mysql service (mariadb) and secures it.

Role Variables
--------------

* ```mysql_root_password```: Password to assign to the `root` user.
* ```mysql_databases```: List of databases to create.
* ```mysql_users```: List of mysql users to be added.  Users have the following format:
```
- name: keystone
  password: iamapassword
  priv: "keystone.*:ALL,GRANT" # Priveleges to be applied
  host: "%" # Host the user is allowed to connect from ('%' is a wildcard)
```
