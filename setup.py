from setuptools import setup

from common_utils.local_debug import IS_PI

installs = ['pytest',
            'pygame==1.9.6',
            'requests']

if IS_PI:
    installs += 'bluepy'

setup(
    name='StratuxHud',
    version='2.0',
    python_requires='>=3.8',
    description='Graphics for a Heads Up Display projector powered by a Stratux receiver.',
    url='https://github.com/JohnMarzulli/StratuxHud',
    author='John Marzulli',
    author_email='john.marzulli@hotmail.com',
    license='GPL V3',
    install_requires=installs)
