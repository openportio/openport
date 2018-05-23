from setuptools import setup, find_packages

install_reqs = [
    'setuptools==39.2.0',
    'paramiko==1.17',  # to avoid "Multibackend cannot be initialized with no backends" error',
    'CherryPy==8.1.2',
    'SQLAlchemy==1.1.1',
    'alembic==0.7.6',
    'argparse==1.4.0',
    'bottle==0.12.10',
    'cryptography==2.2.2',
    'enum34==1.1.6',
    'ipaddress==1.0.17',
    'lockfile==0.12.2',
    'psutil==4.3.1',
    'pyOpenSSL==18.0.0',
    'pycrypto==2.6.1',
    'requests==2.9.1',
    'six==1.10.0',
]

setup(name='openport',
      version='1.0',
      description='Official Openport Client',
      author='Jan De Bleser',
      author_email='jan@openport.io',
      install_requires=install_reqs,
      url='https://openport.io',
      packages=['openport'],
      )
