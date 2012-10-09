from fabric.api import *
from fragrant import vagrant
from fragrant.contrib.filecache import FileCache
from fragrant.vbox import Vbox
from fabric.context_managers import prefix
from fabric.contrib.files import exists, contains, append, comment, uncomment
from fabric.contrib.console import confirm
from fabric.colors import *
from os import path
from clom import clom
from clom.arg import Arg
import shutil
import os
import logging
import json

log = logging.getLogger(__name__)

env.CACHE_DIR = path.expanduser('~/.fragrant/cache')
env.REMOTE_CACHE_DIR = '~/.provision/cache'
env.APT_FAST = None
env.PYTHON_VERSION = '2.7.2'
env.PYTHON_BIN = "/usr/local/pythonbrew/pythons/Python-2.7.2/bin"
env.PYTHON = env.PYTHON_BIN + '/python'
env.PIP = env.PYTHON_BIN + '/pip'
env.HOME = '/home/vagrant'
env.BASH_PROFILE = path.join(env.HOME, '.profile')
env.UBUNTU_VERSION = 'precise'
env.NAME = 'python27'
env.DIR = '/tmp/%s' % env.NAME
env.BASE_DIR = path.dirname(__file__)

filecache = FileCache(env.CACHE_DIR)

def download(url):
    filepath = filecache.get(url)
    filename = path.basename(filepath)
    remotepath = path.join(env.REMOTE_CACHE_DIR, filename)

    if not exists(remotepath):
        if not exists(path.dirname(remotepath)):
            # Using Arg here because LiteralArg escapes ~ and prevents user expansion
            run(clom.mkdir(Arg(path.dirname(remotepath)), p=True))

        put(filepath, remotepath)

    return remotepath

def which(command):
    with settings(hide('everything'), warn_only=True):
        return run(clom.which(command)).succeeded

def configure_make_install(url):
    """
    Download a tgz and run ./configure && make && make install
    """
    remotepath = download(url)
    with cd('/tmp'):
        if exists('build'):
            run('rm -Rf build')

        run('mkdir -p build')
        with cd('build'):
            run('tar zxf %s' % remotepath)
            dir = run('ls | head -1')
            with cd(dir):
                run('./configure')
                run('make')
                sudo('make install')

def apt_install(packages):
    """
    Install a package with apt
    """
    if env.APT_FAST is None:
        env.APT_FAST = which('apt-fast')

    command = 'apt-get'
    if env.APT_FAST:
        command = 'apt-fast'

    if not isinstance(packages, list):
        packages = packages.split(' ')

    with prefix('export DEBIAN_FRONTEND=noninteractive'):
        sudo(clom[command].install(*packages, y=True, q=True).with_opts('--force-yes'))

def add_apt_repository(repo):
    sudo(clom['add-apt-repository'](repo, y=True))
    apt_update()

def apt_update():
    command = 'apt-get'
    if env.APT_FAST:
        command = 'apt-fast'

    sudo('%s -q update' % command)

class Action(object):
    """
    A an action to run on a box.
    """
    def test(self):
        """
        Return True to `run` or False to `fail`
        """

    def run(self):
        """
        Run if `test` returns True
        """
        pass

    def fail(self):
        """
        Run if `test` returns False
        """
        pass

class AptFast(Action):
    name = 'apt-fast'

    def test(self):
        return which('apt-fast')

    def fail(self):
        sudo('apt-get -q update')
        apt_install('python-software-properties')
        sudo('add-apt-repository -y ppa:apt-fast/stable')
        sudo('apt-get -q update')
        apt_install('axel')
        apt_install('apt-fast')

        # Reset apt-fast
        env.APT_FAST = None

    def run(self):
        sudo('apt-fast -q update')

class Pythonbrew(Action):
    name = 'pythonbrew'

    def test(self):
        return which('pythonbrew')

    def fail(self):
        remotepath = download('http://xrl.us/pythonbrewinstall')
        sudo(clom.bash(Arg(remotepath)))

class Python(Action):
    name = 'python'

    def __init__(self):
        self.path_text = 'PATH="%s:$PATH"' % env.PYTHON_BIN

    def test(self):
        with settings(warn_only=True):
            s = sudo('pythonbrew list | grep %s' % env.PYTHON_VERSION).succeeded
            c = contains(env.BASH_PROFILE, self.path_text)
            return s and c
                

    def fail(self):
        sudo('pythonbrew uninstall %s' % env.PYTHON_VERSION)
        sudo('pythonbrew install -f %s' % env.PYTHON_VERSION)
        sudo('pythonbrew switch %s' % env.PYTHON_VERSION)
        append(env.BASH_PROFILE, self.path_text)

class Packages(Action):
    name = 'packages'

    def test(self):
        return True

    def run(self):
        apt_install([
            'unattended-upgrades',
            'build-essential',
            'libssl-dev',
            'libexpat1-dev',
            'pkg-config',
            'git-core',
            'git-flow',
            'curl',
            'vim',
            # Python reqs
            'libjpeg-dev',
            'libsqlite3-dev',
            'libbz2-dev',
            # lxml
            'libxml2-dev',
            'libxslt1-dev'
        ])

class RubyBundler(Action):
    name = 'bundler'

    def test(self):
        return which('bundle')

    def fail(self):
         sudo('gem install bundler')

class VirtualEnvWrapper(Action):
    name = 'virtualenvwrapper'

    def test(self):
        return exists(path.join(env.PYTHON_BIN, 'virtualenvwrapper.sh')) and \
            contains(env.BASH_PROFILE, 'WORKON_HOME')

    def fail(self):
        sudo('%s install virtualenvwrapper' % env.PIP)
        append(env.BASH_PROFILE, 
            'export WORKON_HOME=$HOME/VirtualEnvs\n' +
            'export PROJECT_HOME=$HOME/Dropbox/Projects\n' +
            ('export VIRTUALENVWRAPPER_PYTHON=%s\n' % env.PYTHON) +
            '# Do not run virtualenvwrapper if logged in as another user\n' +
            'if [ $USER == "vagrant" ]; then\n' +
            ('  source %s/virtualenvwrapper.sh\n' % env.PYTHON_BIN) +
            'fi\n'
        )

class VirtualEnv(Action):
    """
    Create a default virtual environment called 'python'
    """
    name = 'virtualenv'

    def test(self):
        return exists('$WORKON_HOME/python')

    def fail(self):
        run('mkvirtualenv --distribute --python "$VIRTUALENVWRAPPER_PYTHON" python')        

class NodeJs(Action):
    name = 'node.js'

    def test(self):
        return which('node')

    def fail(self):
        add_apt_repository('ppa:chris-lea/node.js')
        apt_install('nodejs npm')

class Redis(Action):
    name = 'redis'

    def test(self):
        return which('redis-server')

    def fail(self):
        add_apt_repository('ppa:chris-lea/redis-server')
        apt_install('redis-server')

class MongoDb(Action):
    name = 'mongodb'

    def _is_configured(self):
        return contains('/etc/mongodb.conf', r'#\s*nojournal', escape=False)

    def test(self):
        return which('mongo') and self._is_configured()

    def fail(self):        
        if not contains('/etc/apt/sources.list', '10gen'):
            sudo('apt-key adv --keyserver keyserver.ubuntu.com --recv 7F0CEB10')
            append('/etc/apt/sources.list', 'deb http://downloads-distro.mongodb.org/repo/debian-sysvinit dist 10gen', use_sudo=True)
            apt_update()

        apt_install('mongodb20-10gen')

        # Turn on journaling -- this is a test server, we don't care about the 2GB limit
        if not self._is_configured():
            # Do this manually instead of using `comment` because a bug in Fabric causes a "cd not found" error
            sudo("sed -i.bak -r -e 's/^\s*(nojournal = true\s*)$/#\1/g' /etc/mongodb.conf")

        sudo('/etc/init.d/mongodb restart')

class CleanUp(Action):
    """
    Remove some un-needed files after install completes
    """
    name = 'cleanup'

    def test(self):
        return True

    def run(self):
        sudo('apt-get clean')
        run('rm -Rf /tmp/build')
        run(clom.rm(env.REMOTE_CACHE_DIR, R=True, f=True))        

@task
def provision():
    """
    Create the VM base box
    """
    if path.exists(env.DIR):
        if confirm('%s exists, delete?' % env.DIR, default=False):
            if confirm('Destroy VM too?', default=False):
                with lcd(env.DIR):
                    local('vagrant destroy', capture=False)

            local('rm -Rf %s' % env.DIR)

    if not path.exists(env.DIR):
        os.makedirs(env.DIR)

    shutil.copy('Vagrantfile', env.DIR)

    actions = [
        # Disable apt-fast till noninteractive install is working
        # AptFast(),
        Packages(),
        Pythonbrew(),
        Python(),
        VirtualEnvWrapper(),
        VirtualEnv(),
        NodeJs(),
        RubyBundler(),
        MongoDb(),
        Redis(),
        CleanUp()
    ]

    with lcd(env.DIR):
        with vagrant.session():
            for action in actions:
                with cd('~'):
                    if action.test():
                        puts(cyan('Running task %s:run' % (action.name, )))
                        action.run()
                    else:
                        puts(yellow('Running task %s:fail' % (action.name, )))
                        action.fail()


@task
def package():
    """
    Package the base box
    """
    with lcd(env.DIR):
        with open(path.join(env.DIR, '.vagrant')) as f:
            base = json.load(f)["active"]["default"]

        local(vagrant.vagrant.package.with_opts(base=base, output='%s.box' % env.NAME, include=path.join(env.BASE_DIR, 'fabfile.py'), vagrantfile=path.join(env.BASE_DIR, 'Vagrantfile.pkg'))(env.NAME))
