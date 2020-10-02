import os

from setuptools import setup, find_packages

install_reqs = [
    'paramiko==2.7.2',
    'CherryPy==18.6.0',
    'SQLAlchemy==1.3.19',
    'alembic==1.4.3',
    'argparse==1.4.0',
    'bottle==0.12.18',
    'cryptography==3.1.1',
    'ipaddress==1.0.23',
    'lockfile==0.12.2',
    'psutil==5.7.2',
    'pyOpenSSL==19.1.0',
    'pycrypto==2.6.1',
    'requests==2.24.0',
    'six==1.15.0',
]

def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths

package_data = package_files('openport/alembic')


setup(name='openport',
      version='1.0',
      description='Official Openport Client',
      author='Jan De Bleser',
      author_email='jan@openport.io',
      install_requires=install_reqs,
      url='https://openport.io',
      packages=find_packages(),
      package_data={'': package_data},
      scripts=['bin/openport'],
      )
