====================
Fragrant Python Base
====================

A project that illustrates how to create a Python `vagrant <http://vagrantup.com/>`_ base box with `Fragrant <https://github.com/six8/fragrant>`_.

About
-----

This will create a Vagrant base box for Python development with the following features:

- Ubuntu Precise 32
- Python 2.7 (via `pythonbrew <https://github.com/utahta/pythonbrew>`_)
- Mongo 2.x
- Redis
- PIL dependancies (so you can ``pip install PIL``)
- lxml dependancies (so you can ``pip install lxml``)
- `git flow <https://github.com/nvie/gitflow>`_
- `virtualenvwrapper <http://pypi.python.org/pypi/virtualenvwrapper>`_
- A default virtualenv called 'python' (``workon python``)
- node.js
- apt-fast

Since this is a simple fabric script, it's trivial to change to fit your needs.

Get Started
-----------

Follow the installation instructions for VirtualBox and Vagrant on the `Vagrant Getting Started Guide <http://vagrantup.com/v1/docs/getting-started/index.html>`_. Ignore the section "Your First Vagrant Virtual Environment" as you'll use these fragrant scripts to setup your first virtual environment.

Requirements
~~~~~~~~~~~~

These provision instructions only work for Mac.

Create Vagrant Box
==================

Now it's time to provision your Vagrant box.

Prerequisites
~~~~~~~~~~~~~

Make sure pip is installed::

    which pip || sudo easy_install pip

Once you have pip installed, you'll need a couple of packages::

    pip install -r requirements.txt

Install the linux base box::

    vagrant box add precise32 http://files.vagrantup.com/precise32.box

Provision
~~~~~~~~~

Provision the virtual box (this will take a long time)::
    
    fab provision

If provision fails, fix the problem and run again. It's designed to recover where it left off.

Package
~~~~~~~

Create a vagrant .box::

    fab package
    vagrant box add python27 python27.box

Use Vagrant Box
===============

Add Base Box
-------------

Add the base box to your system::
    
    vagrant box add python27 python27.box    

Creating Your VM    
----------------

Once you have the python27 base box installed, creating a VM is pretty simple. Instructions are for Mac/Linux. You'll need to do similar steps on Windows.

::

    # Create a directory for the VM
    mkdir -p ~/VagrantBoxes/myproject
    # Change to the directory
    cd ~/VagrantBoxes/myproject
    # Initialize VM
    vagrant init python27

Configure
---------

`vagrant init` puts a Vagrantfile in your VM directory. You'll need to edit it for your personal setup.

By default, it expects your code to be in "~/Dropbox/Projects", for example "~/Dropbox/Projects/myproject". If you need to use a different directory, add the following to your Vagrantfile::

    config.vm.share_folder "Projects", "~/Dropbox/Projects", "PATH/TO/PROJECTS", :nfs => true

This will setup the virtual box to run on 192.168.33.13 by default. You need to add this to your hosts file::

    echo "192.168.33.12 local.myproject.com" | sudo tee -a /etc/hosts

NOTE: On Windows the hosts file is different, see http://helpdeskgeek.com/windows-7/windows-7-hosts-file/    

Running VM
----------

Run your Vagrant box and SSH in::

    cd ~/VagrantBoxes/myproject
    vagrant up
    vagrant ssh

When SSHed into your Vagrant box, your code is in ~/Dropbox/Projects. You need to activate the Python virtual environment::

    workon python

You can set your default directory for your virtual environment::

    cd ~/Dropbox/Projects/myproject
    setvirtualenvproject

