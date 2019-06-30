import lib.local_debug as local_debug
import configuration
from setuptools import setup

installs = ['pytest',
            'pygame',
            'ws4py',
            'requests',
            'bluepy']


setup(name='StratuxHud',
      version=configuration.VERSION,
      python_requires='>=2.7',
      description='Graphics for a Heads Up Display projector powered by a Stratux receiver.',
      url='https://github.com/JohnMarzulli/StratuxHud',
      author='John Marzulli',
      author_email='john.marzulli@hotmail.com',
      license='GPL V3',
      install_requires=installs
      )
